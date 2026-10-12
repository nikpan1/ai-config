import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppComponent } from './app.component';
import { ProfileApi } from './profile-api';
import { TradingApi } from './trading-api';

describe('AppComponent profile journey', () => {
  const draft = { draftId: 'D-100', investorRef: 'INV-100', questionnaireVersion: 'Q3', status: 'DRAFT', revision: 1 };
  const result = { assessmentId: 'P-100', investorRef: 'INV-100', providerAssessmentId: 'rs-100', band: 'R2', rulesVersion: 'RS-2026-09', reasonCodes: 'HORIZON_3,LOSS_5', acceptedAt: '2026-10-01T12:00:00Z', status: 'ACTIVE' };
  const profile = { start: vi.fn(() => of(draft)), save: vi.fn(() => of(draft)), submit: vi.fn(() => of(result)), history: vi.fn(() => of([result])) };
  const trading = { quote: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({ imports: [AppComponent], providers: [{ provide: ProfileApi, useValue: profile }, { provide: TradingApi, useValue: trading }] });
  });

  it('shows an accepted result and history without calling trading', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.start();
    fixture.componentInstance.consent = true;
    fixture.componentInstance.save();
    fixture.componentInstance.submit();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Accepted band R2');
    expect(fixture.nativeElement.textContent).toContain('RS-2026-09');
    expect(fixture.nativeElement.textContent).toContain('rs-100');
    expect(profile.submit).toHaveBeenCalledOnce();
    expect(trading.quote).not.toHaveBeenCalled();
  });
});
