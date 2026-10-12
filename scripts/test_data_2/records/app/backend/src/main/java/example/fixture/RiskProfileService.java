package example.fixture;

import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.server.ResponseStatusException;

@Service
public class RiskProfileService {
    private final ProfileRepository profiles;
    private final RiskSignalClient riskSignal;
    private final MongoAuditRepository audits;

    public RiskProfileService(ProfileRepository profiles, RiskSignalClient riskSignal, MongoAuditRepository audits) {
        this.profiles = profiles;
        this.riskSignal = riskSignal;
        this.audits = audits;
    }

    @Transactional
    public ProfileDtos.Draft start(String investorRef) {
        String status = profiles.investorStatus(investorRef);
        if (!status.equals("ACTIVE") && !status.equals("PENDING")) throw new IllegalStateException("Investor cannot start a draft");
        return profiles.openDraft(investorRef).orElseGet(() -> profiles.createDraft(investorRef));
    }

    @Transactional
    public ProfileDtos.Draft save(String draftId, ProfileDtos.Answers answers) {
        ProfileDtos.Draft draft = profiles.lockDraft(draftId);
        if (!"DRAFT".equals(draft.status())) throw new IllegalStateException("Draft is not editable");
        validateCodes(answers);
        profiles.saveAnswers(draftId, answers);
        return profiles.lockDraft(draftId);
    }

    @Transactional
    public ProfileDtos.Assessment submit(String draftId, String key) {
        ProfileDtos.Draft draft = profiles.lockDraft(draftId);
        if (!"ACTIVE".equals(profiles.investorStatus(draft.investorRef()))) throw new IllegalStateException("Investor cannot submit");
        if (!"Q3".equals(draft.questionnaireVersion())) throw new IllegalStateException("OUTDATED_QUESTIONNAIRE");
        ProfileDtos.Answers answers = profiles.answers(draftId);
        validateCodes(answers);
        if (!answers.processingConsent()) throw new IllegalArgumentException("PROFILE_PROCESSING consent required");
        profiles.claimKey(key, draftId, answers);
        var existing = profiles.byKey(key);
        if (existing.isPresent()) return existing.get();
        ProfileDtos.ProviderRequest request = new ProfileDtos.ProviderRequest(draft.investorRef(), "Q3", "RS-2026-09", answers.experience(), answers.horizon(), answers.lossTolerance(), answers.liquidityNeed(), "CP-3", key, UUID.randomUUID().toString());
        ProfileDtos.ProviderResponse response;
        try {
            response = assessWithOneRetry(request);
        } catch (RuntimeException error) {
            audits.failure(draftId, request, "PROVIDER_UNAVAILABLE");
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "RiskSignal unavailable", error);
        }
        if (response == null || response.providerAssessmentId() == null || response.providerAssessmentId().isBlank() || response.reasonCodes() == null || response.reasonCodes().length == 0 || response.evaluatedAt() == null || !"RS-2026-09".equals(response.responseRulesVersion()) || !Arrays.asList("R1", "R2", "R3", "R4").contains(response.proposedBand())) {
            audits.failure(draftId, request, "INCOMPLETE_RESPONSE");
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Incomplete RiskSignal response");
        }
        audits.success(draftId, request, response);
        profiles.accept(draftId, key, response);
        return profiles.byKey(key).orElseThrow();
    }

    public List<ProfileDtos.Assessment> history(String investorRef) {
        return profiles.history(investorRef);
    }

    private void validateCodes(ProfileDtos.Answers answers) {
        if (!profiles.allowed("experience-level", answers.experience()) || !profiles.allowed("investment-horizon", answers.horizon()) || !profiles.allowed("loss-tolerance", answers.lossTolerance()) || !profiles.allowed("liquidity-need", answers.liquidityNeed())) {
            throw new IllegalArgumentException("Invalid questionnaire code");
        }
    }

    private ProfileDtos.ProviderResponse assessWithOneRetry(ProfileDtos.ProviderRequest request) {
        try {
            return riskSignal.assess(request);
        } catch (ResourceAccessException | HttpServerErrorException.ServiceUnavailable retryable) {
            return riskSignal.assess(request);
        }
    }
}
