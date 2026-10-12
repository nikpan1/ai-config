import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { describe, expect, it, afterEach, beforeEach } from 'vitest';
import { ProfileApi } from './profile-api';

describe('ProfileApi', () => {
  let api: ProfileApi;
  let requests: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ProfileApi);
    requests = TestBed.inject(HttpTestingController);
  });

  afterEach(() => requests.verify());

  it('sends the same idempotency key when submission is retried', () => {
    const key = 'fixture-key-100';
    api.submit('D-100', key).subscribe({ error: () => {} });
    const first = requests.expectOne('/api/profile/drafts/D-100/submit');
    expect(first.request.body.idempotencyKey).toBe(key);
    first.flush('temporary failure', { status: 503, statusText: 'Unavailable' });
    api.submit('D-100', key).subscribe();
    const second = requests.expectOne('/api/profile/drafts/D-100/submit');
    expect(second.request.body.idempotencyKey).toBe(key);
    second.flush({ assessmentId: 'P-100', investorRef: 'INV-100', providerAssessmentId: 'rs-100', band: 'R2', rulesVersion: 'RS-2026-09', reasonCodes: 'HORIZON_3', acceptedAt: '2026-10-01T12:00:00Z', status: 'ACTIVE' });
  });
});
