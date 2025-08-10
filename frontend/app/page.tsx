"use client";

import { Suspense } from "react";

import Home from "@/components/home";

export default function Page() {
  return (
    <Suspense fallback={<></>}>
      <Home />
    </Suspense>
  );
}
