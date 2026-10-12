package example.fixture;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class ProfileRepository {
    private final JdbcTemplate db;
    private final ObjectMapper json;

    public ProfileRepository(JdbcTemplate db, ObjectMapper json) {
        this.db = db;
        this.json = json;
    }

    public String investorStatus(String investorRef) {
        return db.queryForObject("select status from investor where investor_ref = ?", String.class, investorRef);
    }

    public Optional<ProfileDtos.Draft> openDraft(String investorRef) {
        return db.query("select draft_id, investor_ref, questionnaire_version, status, revision from profile_draft where investor_ref = ? and status = 'DRAFT' order by created_at desc limit 1", this::draft, investorRef).stream().findFirst();
    }

    public ProfileDtos.Draft createDraft(String investorRef) {
        String id = UUID.randomUUID().toString();
        db.update("insert into profile_draft(draft_id, investor_ref, questionnaire_version, status, revision) values (?, ?, 'Q3', 'DRAFT', 0)", id, investorRef);
        return new ProfileDtos.Draft(id, investorRef, "Q3", "DRAFT", 0);
    }

    public ProfileDtos.Draft lockDraft(String draftId) {
        return db.query("select draft_id, investor_ref, questionnaire_version, status, revision from profile_draft where draft_id = ? for update", this::draft, draftId).stream().findFirst().orElseThrow(() -> new IllegalArgumentException("Draft not found"));
    }

    public boolean allowed(String dictionary, String code) {
        Integer count = db.queryForObject("select count(*) from dictionary_code where dictionary_name = ? and code = ? and revision = 'D-2026-09' and retired = false", Integer.class, dictionary, code);
        return count != null && count > 0;
    }

    public void saveAnswers(String draftId, ProfileDtos.Answers answers) {
        int changed = db.update("update profile_draft set answers = ?::jsonb, consent_revision = ?, consent_at = case when ? then now() else null end, revision = revision + 1 where draft_id = ? and status = 'DRAFT' and revision = ?", serialize(answers), answers.processingConsent() ? "CP-3" : null, answers.processingConsent(), draftId, answers.revision());
        if (changed != 1) throw new IllegalStateException("Draft revision conflict");
    }

    public ProfileDtos.Answers answers(String draftId) {
        String content = db.queryForObject("select answers::text from profile_draft where draft_id = ?", String.class, draftId);
        if (content == null) throw new IllegalArgumentException("Answers required");
        try {
            return json.readValue(content, ProfileDtos.Answers.class);
        } catch (JsonProcessingException error) {
            throw new IllegalStateException("Stored answers invalid", error);
        }
    }

    public Optional<ProfileDtos.Assessment> byKey(String key) {
        return db.query("select assessment_id, investor_ref, provider_assessment_id, band, rules_version, reason_codes, accepted_at, status from profile_summary where idempotency_key = ?", this::assessment, key).stream().findFirst();
    }

    public void claimKey(String key, String draftId, ProfileDtos.Answers answers) {
        String hash = hash(String.join("|", answers.experience(), answers.horizon(), answers.lossTolerance(), answers.liquidityNeed(), Boolean.toString(answers.processingConsent())));
        db.update("insert into submission_key(idempotency_key, draft_id, answer_hash) values (?, ?, ?) on conflict (idempotency_key) do nothing", key, draftId, hash);
        List<String> matching = db.query("select idempotency_key from submission_key where idempotency_key = ? and draft_id = ? and answer_hash = ? for update", (row, ignored) -> row.getString(1), key, draftId, hash);
        if (matching.isEmpty()) throw new IllegalStateException("Idempotency key conflicts with another submission");
    }

    public void accept(String draftId, String key, ProfileDtos.ProviderResponse response) {
        ProfileDtos.Draft draft = lockDraft(draftId);
        db.update("update profile_summary set status = 'SUPERSEDED' where investor_ref = ? and status = 'ACTIVE'", draft.investorRef());
        db.update("insert into profile_summary(assessment_id, investor_ref, draft_id, questionnaire_version, rules_version, provider_assessment_id, band, reason_codes, accepted_at, status, idempotency_key) values (?, ?, ?, 'Q3', ?, ?, ?, ?, ?, 'ACTIVE', ?)", UUID.randomUUID().toString(), draft.investorRef(), draftId, response.responseRulesVersion(), response.providerAssessmentId(), response.proposedBand(), String.join(",", response.reasonCodes()), response.evaluatedAt(), key);
        db.update("update profile_draft set status = 'SUBMITTED' where draft_id = ?", draftId);
    }

    public List<ProfileDtos.Assessment> history(String investorRef) {
        return db.query("select assessment_id, investor_ref, provider_assessment_id, band, rules_version, reason_codes, accepted_at, status from profile_summary where investor_ref = ? order by accepted_at desc", this::assessment, investorRef);
    }

    private ProfileDtos.Draft draft(ResultSet row, int ignored) throws SQLException {
        return new ProfileDtos.Draft(row.getString("draft_id"), row.getString("investor_ref"), row.getString("questionnaire_version"), row.getString("status"), row.getLong("revision"));
    }

    private ProfileDtos.Assessment assessment(ResultSet row, int ignored) throws SQLException {
        Instant acceptedAt = row.getTimestamp("accepted_at").toInstant();
        String status = row.getString("status");
        if ("ACTIVE".equals(status) && !acceptedAt.plusSeconds(365L * 24 * 3600).isAfter(Instant.now())) status = "EXPIRED";
        return new ProfileDtos.Assessment(row.getString("assessment_id"), row.getString("investor_ref"), row.getString("provider_assessment_id"), row.getString("band"), row.getString("rules_version"), row.getString("reason_codes"), acceptedAt, status);
    }

    private String serialize(Object value) {
        try {
            return json.writeValueAsString(value);
        } catch (JsonProcessingException error) {
            throw new IllegalArgumentException("Answers cannot be serialized", error);
        }
    }

    private String hash(String content) {
        try {
            byte[] value = MessageDigest.getInstance("SHA-256").digest(content.getBytes(StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(value);
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }
}
