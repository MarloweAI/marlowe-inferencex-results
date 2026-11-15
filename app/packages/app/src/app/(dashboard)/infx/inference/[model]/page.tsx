import type { Metadata } from 'next';
import { notFound } from 'next/navigation';


import { InferencePageIntro } from '@/components/inference/inference-page-intro';
import { InferenceProvider } from '@/components/inference/InferenceContext';
import InferenceChartDisplay from '@/components/inference/ui/ChartDisplay';
import { MarloweNotes } from '@/components/marlowe/marlowe-notes';
import { MARLOWE_MODEL_SLUGS } from '@/components/marlowe/models';
import { inferenceModelMeta } from '@/lib/routing/inference-model-meta';
import {
  getInferenceModelBySlug,
  PUBLIC_INFERENCE_MODEL_SLUGS,
} from '@/lib/routing/inference-model-slug';

interface Props {
  params: Promise<{ model: string }>;
}

export const dynamicParams = false;

export function generateStaticParams(): { model: string }[] {
  return PUBLIC_INFERENCE_MODEL_SLUGS.filter((entry) => MARLOWE_MODEL_SLUGS.includes(entry.slug)).map(
    (entry) => ({ model: entry.slug }),
  );
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { model } = await params;
  const entry = getInferenceModelBySlug(model);
  if (!entry) return {};
  const { title, description } = inferenceModelMeta(entry);
  return { title: { absolute: `${title} | Marlowe` }, description };
}

export default async function InferenceModelPage({ params }: Props) {
  const { model } = await params;
  const entry = getInferenceModelBySlug(model);
  if (!entry) notFound();
  return (
    <>
      <InferencePageIntro locale="en" />
      <InferenceProvider activeTab="inference">
        <InferenceChartDisplay centerOnEnter />
      </InferenceProvider>
      <MarloweNotes />
    </>
  );
}
