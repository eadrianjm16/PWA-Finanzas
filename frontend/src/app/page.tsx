"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated === null) return;
    router.replace(isAuthenticated ? "/accounts" : "/login");
  }, [isAuthenticated, router]);

  return null;
}
