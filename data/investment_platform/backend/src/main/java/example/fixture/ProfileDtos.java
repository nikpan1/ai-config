package example.fixture;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;

public final class ProfileDtos {
    private ProfileDtos() {}

    public record StartDraft(@NotBlank String investorRef) {}
    public record Draft(String draftId, String investorRef, String questionnaireVersion, String status, long revision) {}
    public record Answers(@NotBlank String experience, @NotBlank String horizon, @NotBlank String lossTolerance, @NotBlank String liquidityNeed, boolean processingConsent, @NotNull Long revision) {}
    public record Submit(@NotBlank String idempotencyKey) {}
    public record Assessment(String assessmentId, String investorRef, String providerAssessmentId, String band, String rulesVersion, String reasonCodes, Instant acceptedAt, String status) {}
    public record ProviderRequest(String investorRef, String questionnaireVersion, String rulesVersion, String experience, String horizon, String lossTolerance, String liquidityNeed, String consentRevision, String idempotencyKey, String correlationId) {}
    public record ProviderResponse(String providerAssessmentId, String proposedBand, String[] reasonCodes, String responseRulesVersion, Instant evaluatedAt) {}
}
