import client from './client';

export async function submitFeedback(
  rating: number,
  topFeature: string,
  comment?: string,
): Promise<void> {
  await client.post('/v1/feedback', {
    rating,
    top_feature: topFeature,
    comment: comment ?? null,
    source: 'miniapp',
  });
}
