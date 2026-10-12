db = db.getSiblingDB("investment_fixture");
db.createCollection("answer_snapshots");
db.createCollection("risk_audits");
db.answer_snapshots.createIndex({ draftId: 1, questionnaireVersion: 1 });
db.risk_audits.createIndex({ correlationId: 1 });
db.risk_audits.createIndex({ providerAssessmentId: 1 }, { sparse: true });
db.risk_audits.insertOne({ draftId: "historical-D-031", questionnaireVersion: "Q2", correlationId: "corr-historical-031", providerAssessmentId: "rs-historical-031", status: "SUCCEEDED", rulesVersion: "RS-2026-01", reasonCodes: ["HORIZON_SHORT"], recordedAt: ISODate("2026-02-14T11:00:00Z") });
