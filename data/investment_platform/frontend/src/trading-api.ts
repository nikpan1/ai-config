import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface Quote { instrumentId: string; bid: number; ask: number; quoteCurrency: string; session: string; instrumentRisk: string; asOf: string }

@Injectable({ providedIn: 'root' })
export class TradingApi {
  private readonly http = inject(HttpClient);

  quote(instrumentId: string): Observable<Quote> {
    return this.http.get<Quote>(`/api/trading/quotes/${encodeURIComponent(instrumentId)}`);
  }
}
