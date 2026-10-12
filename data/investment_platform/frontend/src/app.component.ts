import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Assessment, Answers, Draft, ProfileApi } from './profile-api';
import { Quote, TradingApi } from './trading-api';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html'
})
export class AppComponent {
  private readonly api = inject(ProfileApi);
  private readonly trading = inject(TradingApi);
  view: 'profile' | 'history' | 'quotes' = 'profile';
  investorRef = 'INV-100';
  draft?: Draft;
  result?: Assessment;
  history: Assessment[] = [];
  error = '';
  consent = false;
  answers: Answers = { experience: 'BEGINNER', horizon: 'H3', lossTolerance: 'L5', liquidityNeed: 'FLEXIBLE', processingConsent: false, revision: 0 };
  quoteInstrument = 'XS0000000001';
  quote?: Quote;
  submissionKey?: string;

  start(): void {
    this.error = '';
    this.api.start(this.investorRef).subscribe({ next: draft => { if (this.draft?.draftId !== draft.draftId) this.submissionKey = undefined; this.draft = draft; this.answers.revision = draft.revision; }, error: error => this.error = error.error || 'Draft could not be opened' });
  }

  save(): void {
    if (!this.draft) return;
    this.error = '';
    this.answers.processingConsent = this.consent;
    this.api.save(this.draft.draftId, this.answers).subscribe({ next: draft => { this.draft = draft; this.answers.revision = draft.revision; }, error: error => this.error = error.error || 'Answers could not be saved' });
  }

  submit(): void {
    if (!this.draft || !this.consent) return;
    this.submissionKey ??= crypto.randomUUID();
    this.api.submit(this.draft.draftId, this.submissionKey).subscribe({ next: result => { this.result = result; this.error = ''; this.loadHistory(); }, error: error => this.error = error.error || 'Assessment unavailable; retry with the same key' });
  }

  loadHistory(): void {
    this.api.history(this.investorRef).subscribe({ next: history => this.history = history, error: error => this.error = error.error || 'History unavailable' });
  }

  loadQuote(): void {
    this.trading.quote(this.quoteInstrument).subscribe({ next: quote => this.quote = quote, error: error => this.error = error.error || 'Quote unavailable' });
  }
}
