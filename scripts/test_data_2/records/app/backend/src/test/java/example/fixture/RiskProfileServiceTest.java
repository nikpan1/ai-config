package example.fixture;

import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.client.ResourceAccessException;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class RiskProfileServiceTest {
    private ProfileRepository profiles;
    private RiskSignalClient riskSignal;
    private MongoAuditRepository audits;
    private RiskProfileService service;
    private ProfileDtos.Answers answers;

    @BeforeEach
    void setup() {
        profiles = mock(ProfileRepository.class);
        riskSignal = mock(RiskSignalClient.class);
        audits = mock(MongoAuditRepository.class);
        service = new RiskProfileService(profiles, riskSignal, audits);
        answers = new ProfileDtos.Answers("BEGINNER", "H3", "L5", "FLEXIBLE", true, 1L);
        when(profiles.allowed(anyString(), anyString())).thenReturn(true);
        when(profiles.lockDraft("D-100")).thenReturn(new ProfileDtos.Draft("D-100", "INV-100", "Q3", "DRAFT", 1));
        when(profiles.investorStatus("INV-100")).thenReturn("ACTIVE");
        when(profiles.answers("D-100")).thenReturn(answers);
    }

    @Test
    void submissionPersistsRiskSignalResultWithoutTradingCalls() {
        ProfileDtos.ProviderResponse proposal = new ProfileDtos.ProviderResponse("rs-100", "R2", new String[] {"HORIZON_3", "LOSS_5"}, "RS-2026-09", Instant.parse("2026-10-01T12:00:00Z"));
        ProfileDtos.Assessment accepted = new ProfileDtos.Assessment("P-100", "INV-100", "rs-100", "R2", "RS-2026-09", "HORIZON_3,LOSS_5", proposal.evaluatedAt(), "ACTIVE");
        when(riskSignal.assess(any())).thenReturn(proposal);
        when(profiles.byKey("key-100")).thenReturn(Optional.empty(), Optional.of(accepted));
        assertEquals(accepted, service.submit("D-100", "key-100"));
        verify(riskSignal).assess(any());
        verify(audits).success(eq("D-100"), any(), eq(proposal));
        verify(profiles).accept("D-100", "key-100", proposal);
    }

    @Test
    void duplicateReturnsAcceptedProfileWithoutSecondProviderCall() {
        ProfileDtos.Assessment accepted = new ProfileDtos.Assessment("P-100", "INV-100", "rs-100", "R2", "RS-2026-09", "HORIZON_3", Instant.parse("2026-10-01T12:00:00Z"), "ACTIVE");
        when(profiles.byKey("key-100")).thenReturn(Optional.of(accepted));
        assertEquals(accepted, service.submit("D-100", "key-100"));
        verifyNoInteractions(riskSignal, audits);
    }

    @Test
    void incompleteResponseCannotBeAccepted() {
        when(profiles.byKey("key-100")).thenReturn(Optional.empty());
        when(riskSignal.assess(any())).thenReturn(new ProfileDtos.ProviderResponse("rs-100", "R2", new String[0], "RS-2026-09", Instant.parse("2026-10-01T12:00:00Z")));
        assertThrows(ResponseStatusException.class, () -> service.submit("D-100", "key-100"));
        verify(profiles, never()).accept(anyString(), anyString(), any());
        verify(audits).failure(eq("D-100"), any(), eq("INCOMPLETE_RESPONSE"));
    }

    @Test
    void invalidAnswerStopsBeforeProvider() {
        when(profiles.allowed("liquidity-need", "FLEXIBLE")).thenReturn(false);
        assertThrows(IllegalArgumentException.class, () -> service.submit("D-100", "key-100"));
        verifyNoInteractions(riskSignal, audits);
    }

    @Test
    void outdatedVersionStopsBeforeProvider() {
        when(profiles.lockDraft("D-100")).thenReturn(new ProfileDtos.Draft("D-100", "INV-100", "Q2", "DRAFT", 1));
        assertThrows(IllegalStateException.class, () -> service.submit("D-100", "key-100"));
        verifyNoInteractions(riskSignal, audits);
    }

    @Test
    void missingProcessingConsentStopsBeforeProvider() {
        when(profiles.answers("D-100")).thenReturn(new ProfileDtos.Answers("BEGINNER", "H3", "L5", "FLEXIBLE", false, 1L));
        assertThrows(IllegalArgumentException.class, () -> service.submit("D-100", "key-100"));
        verifyNoInteractions(riskSignal, audits);
    }

    @Test
    void retryUsesTheSameProviderRequest() {
        ProfileDtos.ProviderResponse proposal = new ProfileDtos.ProviderResponse("rs-100", "R2", new String[] {"HORIZON_3"}, "RS-2026-09", Instant.parse("2026-10-01T12:00:00Z"));
        when(profiles.byKey("key-100")).thenReturn(Optional.empty(), Optional.of(new ProfileDtos.Assessment("P-100", "INV-100", "rs-100", "R2", "RS-2026-09", "HORIZON_3", proposal.evaluatedAt(), "ACTIVE")));
        when(riskSignal.assess(any())).thenThrow(new ResourceAccessException("connect failure")).thenReturn(proposal);
        service.submit("D-100", "key-100");
        org.mockito.ArgumentCaptor<ProfileDtos.ProviderRequest> captured = org.mockito.ArgumentCaptor.forClass(ProfileDtos.ProviderRequest.class);
        verify(riskSignal, times(2)).assess(captured.capture());
        assertEquals(captured.getAllValues().get(0), captured.getAllValues().get(1));
    }

    @Test
    void repeatedProviderOutageDoesNotAcceptAProfile() {
        when(profiles.byKey("key-100")).thenReturn(Optional.empty());
        when(riskSignal.assess(any())).thenThrow(new ResourceAccessException("connect failure"));
        assertThrows(ResponseStatusException.class, () -> service.submit("D-100", "key-100"));
        verify(riskSignal, times(2)).assess(any());
        verify(audits).failure(eq("D-100"), any(), eq("PROVIDER_UNAVAILABLE"));
        verify(profiles, never()).accept(anyString(), anyString(), any());
    }

    @Test
    void mongoWriteFailureBlocksAcceptance() {
        ProfileDtos.ProviderResponse proposal = new ProfileDtos.ProviderResponse("rs-100", "R2", new String[] {"HORIZON_3"}, "RS-2026-09", Instant.parse("2026-10-01T12:00:00Z"));
        when(profiles.byKey("key-100")).thenReturn(Optional.empty());
        when(riskSignal.assess(any())).thenReturn(proposal);
        doThrow(new IllegalStateException("Mongo unavailable")).when(audits).success(eq("D-100"), any(), eq(proposal));
        assertThrows(IllegalStateException.class, () -> service.submit("D-100", "key-100"));
        verify(profiles, never()).accept(anyString(), anyString(), any());
    }

    @Test
    void returningInvestorReopensTheExistingDraft() {
        ProfileDtos.Draft existing = new ProfileDtos.Draft("D-100", "INV-100", "Q3", "DRAFT", 3);
        when(profiles.openDraft("INV-100")).thenReturn(Optional.of(existing));
        assertEquals(existing, service.start("INV-100"));
        verify(profiles, never()).createDraft(anyString());
    }
}
