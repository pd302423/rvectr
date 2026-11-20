"use client";

import { ThreeMeshCanvas } from "@/components/biomechanics/ThreeMeshCanvas";
import { Container } from "@/components/site/Container";
import { Notice } from "@/components/site/Notice";
import { PageHeader } from "@/components/site/PageHeader";

export default function DemoPage() {
  return (
    <Container size="wide" className="grid gap-8 py-10 sm:py-14">
      <PageHeader eyebrow="3D viewer" title="A sample body model in 3D">
        <p>Drag to turn the model, scroll or pinch to zoom. The model plays a pre-made squat animation.</p>
      </PageHeader>

      <Notice title="This is a 3D viewer of a sample body model.">
        <p>
          It is not a measurement of anyone. The squat-depth measurement follows the hips only and does not need a full
          body model. Results from the two-phone software are not shown here yet.
        </p>
      </Notice>

      <section aria-label="3D viewer" className="grid gap-3">
        <ThreeMeshCanvas height="min(540px, 70svh)" glbUrl="/squat_3d_mesh.glb" />
        <p className="max-w-[65ch] text-sm leading-relaxed text-muted-foreground">
          Sample model file: <code className="font-mono text-foreground">public/squat_3d_mesh.glb</code>. If you only see an empty
          floor grid, that file is not installed in this copy of the site.
        </p>
      </section>
    </Container>
  );
}
