import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface Draft { draftId: string; investorRef: string; questionnaireVersion: string; status: string; revision: number }
export interface Answers { experience: string; horizon: string; lossTolerance: string; liquidityNeed: string; processingConsent: boolean; revision: number }
export interface Assessment { assessmentId: string; investorRef: string; providerAssessmentId: string; band: string; rulesVersion: string; reasonCodes: string; acceptedAt: string; status: string }

@Injectable({ providedIn: 'root' })
export class ProfileApi {
  private readonly http = inject(HttpClient);

  start(investorRef: string): Observable<Draft> {
    return this.http.post<Draft>('/api/profile/drafts', { investorRef });
  }

  save(draftId: string, answers: Answers): Observable<Draft> {
    return this.http.patch<Draft>(`/api/profile/drafts/${draftId}`, answers);
  }

  submit(draftId: string, idempotencyKey: string): Observable<Assessment> {
    return this.http.post<Assessment>(`/api/profile/drafts/${draftId}/submit`, { idempotencyKey });
  }

  history(investorRef: string): Observable<Assessment[]> {
    return this.http.get<Assessment[]>(`/api/profile/investors/${investorRef}/history`);
  }
}
