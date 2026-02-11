import { v4 as uuidv4 } from 'uuid';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('X402Mock');

export interface X402Payment {
  paymentId: string;
  from: string;
  to: string;
  amount: number;
  currency: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  protocolVersion: string;
  httpStatusCode: number;
  headers: Record<string, string>;
  createdAt: number;
  settledAt: number | null;
}

export interface X402Ledger {
  totalPayments: number;
  totalVolume: number;
  payments: X402Payment[];
  balances: Map<string, number>;
}

export class X402MockPaymentEngine {
  private ledger: X402Ledger;
  private processingDelayMs: number;

  constructor() {
    this.ledger = {
      totalPayments: 0,
      totalVolume: 0,
      payments: [],
      balances: new Map(),
    };
    this.processingDelayMs = 50;
  }

  async processPayment(
    fromAddress: string,
    toAddress: string,
    amount: number
  ): Promise<X402Payment> {
    const payment: X402Payment = {
      paymentId: uuidv4(),
      from: fromAddress,
      to: toAddress,
      amount,
      currency: 'x402-TOKEN',
      status: 'pending',
      protocolVersion: 'x402/1.0',
      httpStatusCode: 402,
      headers: {
        'X-402-Payment-Required': 'true',
        'X-402-Amount': amount.toString(),
        'X-402-Currency': 'x402-TOKEN',
        'X-402-Payment-Id': '',
        'X-402-Protocol-Version': 'x402/1.0',
      },
      createdAt: Date.now(),
      settledAt: null,
    };

    payment.headers['X-402-Payment-Id'] = payment.paymentId;

    logger.debug('Processing x402 payment', {
      paymentId: payment.paymentId,
      from: fromAddress,
      to: toAddress,
      amount,
    });

    payment.status = 'processing';

    await this.simulateNetworkLatency();

    const success = Math.random() > 0.02;

    if (success) {
      payment.status = 'completed';
      payment.httpStatusCode = 200;
      payment.settledAt = Date.now();

      const currentBalance = this.ledger.balances.get(toAddress) || 0;
      this.ledger.balances.set(toAddress, currentBalance + amount);

      this.ledger.totalVolume += amount;

      logger.info('x402 payment completed', {
        paymentId: payment.paymentId,
        amount,
        newBalance: currentBalance + amount,
      });
    } else {
      payment.status = 'failed';
      payment.httpStatusCode = 500;
      logger.error('x402 payment failed', { paymentId: payment.paymentId });
    }

    this.ledger.payments.push(payment);
    this.ledger.totalPayments++;

    return payment;
  }

  async processBatchPayments(
    payments: Array<{ from: string; to: string; amount: number }>
  ): Promise<X402Payment[]> {
    logger.info('Processing batch x402 payments', { count: payments.length });

    const results = await Promise.all(
      payments.map((p) => this.processPayment(p.from, p.to, p.amount))
    );

    const successful = results.filter((r) => r.status === 'completed');
    const failed = results.filter((r) => r.status === 'failed');

    logger.info('Batch payment complete', {
      total: results.length,
      successful: successful.length,
      failed: failed.length,
      totalVolume: successful.reduce((sum, p) => sum + p.amount, 0),
    });

    return results;
  }

  getBalance(address: string): number {
    return this.ledger.balances.get(address) || 0;
  }

  getAllBalances(): Record<string, number> {
    return Object.fromEntries(this.ledger.balances);
  }

  getPaymentHistory(address?: string): X402Payment[] {
    if (address) {
      return this.ledger.payments.filter(
        (p) => p.from === address || p.to === address
      );
    }
    return [...this.ledger.payments];
  }

  getLedgerStats() {
    return {
      totalPayments: this.ledger.totalPayments,
      totalVolume: Math.round(this.ledger.totalVolume * 100) / 100,
      uniqueRecipients: this.ledger.balances.size,
      averagePayment:
        this.ledger.totalPayments > 0
          ? Math.round((this.ledger.totalVolume / this.ledger.totalPayments) * 100) / 100
          : 0,
      successRate:
        this.ledger.totalPayments > 0
          ? Math.round(
              (this.ledger.payments.filter((p) => p.status === 'completed').length /
                this.ledger.totalPayments) *
                10000
            ) / 100
          : 100,
    };
  }

  private simulateNetworkLatency(): Promise<void> {
    const jitter = Math.random() * this.processingDelayMs;
    return new Promise((resolve) => setTimeout(resolve, this.processingDelayMs + jitter));
  }
}

export const x402Engine = new X402MockPaymentEngine();