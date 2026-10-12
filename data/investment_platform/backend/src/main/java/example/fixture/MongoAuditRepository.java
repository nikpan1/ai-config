package example.fixture;

import java.time.Instant;
import java.util.Date;
import org.bson.Document;
import org.bson.Document;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class MongoAuditRepository {
    private final MongoTemplate mongo;

    public MongoAuditRepository(MongoTemplate mongo) {
        this.mongo = mongo;
    }

    public void success(String draftId, ProfileDtos.ProviderRequest request, ProfileDtos.ProviderResponse response) {
        Document answers = new Document("experience", request.experience()).append("horizon", request.horizon()).append("lossTolerance", request.lossTolerance()).append("liquidityNeed", request.liquidityNeed());
        Document requestRecord = new Document("investorRef", request.investorRef()).append("rulesVersion", request.rulesVersion()).append("idempotencyKey", request.idempotencyKey()).append("consentRevision", request.consentRevision()).append("answers", answers);
        Document responseRecord = new Document("proposedBand", response.proposedBand()).append("reasonCodes", response.reasonCodes()).append("responseRulesVersion", response.responseRulesVersion()).append("evaluatedAt", Date.from(response.evaluatedAt()));
        mongo.insert(new Document("draftId", draftId).append("questionnaireVersion", request.questionnaireVersion()).append("correlationId", request.correlationId()).append("answers", answers).append("recordedAt", Date.from(Instant.now())), "answer_snapshots");
        mongo.insert(new Document("draftId", draftId).append("questionnaireVersion", request.questionnaireVersion()).append("correlationId", request.correlationId()).append("providerAssessmentId", response.providerAssessmentId()).append("request", requestRecord).append("response", responseRecord).append("status", "SUCCEEDED").append("recordedAt", Date.from(Instant.now())), "risk_audits");
    }

    public void failure(String draftId, ProfileDtos.ProviderRequest request, String reason) {
        mongo.insert(new Document("draftId", draftId).append("questionnaireVersion", request.questionnaireVersion()).append("correlationId", request.correlationId()).append("idempotencyKey", request.idempotencyKey()).append("status", "FAILED").append("reason", reason).append("recordedAt", Date.from(Instant.now())), "risk_audits");
    }
}
