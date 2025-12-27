import { NextResponse } from 'next/server';
import { CLAIM_CHECK_DEFAULTS } from '@/config/constants';
import { runClaimCheck } from '@/lib/claimCheck';
import type { ClaimCheckRequest } from '@/types/claimCheck';

const { MIN_MINERS, MAX_MINERS } = CLAIM_CHECK_DEFAULTS;

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as ClaimCheckRequest | null;

    if (!payload || typeof payload !== 'object') {
      return NextResponse.json({ error: 'Invalid JSON payload.' }, { status: 400 });
    }

    const { claim, context_url = null, context_text = null, client_reference = null } = payload;
    const numMinersInput = payload.num_miners;

    if (!claim?.trim()) {
      return NextResponse.json({ error: 'Claim is required.' }, { status: 400 });
    }

    if (
      numMinersInput !== undefined &&
      (Number.isNaN(numMinersInput) || numMinersInput < MIN_MINERS || numMinersInput > MAX_MINERS)
    ) {
      return NextResponse.json(
        { error: `num_miners must be between ${MIN_MINERS} and ${MAX_MINERS}.` },
        { status: 400 },
      );
    }

    const response = await runClaimCheck({
      claim,
      context_url,
      context_text,
      num_miners: numMinersInput,
      client_reference,
    });

    return NextResponse.json(response);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unexpected error occurred.';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
