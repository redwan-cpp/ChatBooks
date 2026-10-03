"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CompanionMark, MoneyCompanion } from "@/components/money-companion";
import { Button, Field, Notice } from "@/components/ui";

import { useAuth } from "./auth-provider";

export function AuthScreen({ mode }: { mode: "login" | "register" }) {
  const { status, login, register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace(searchParams.get("next") || "/chat");
  }, [router, searchParams, status]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      if (mode === "register") await register(name, username, password);
      else await login(username, password);
      router.replace(searchParams.get("next") || "/chat");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The request could not be completed.");
    } finally {
      setSubmitting(false);
    }
  }

  const registering = mode === "register";
  return (
    <main className="auth-screen">
      <section className="auth-story">
        <div className="brand light">
          <CompanionMark />
          <span>
            <strong>Chatbooks</strong>
            <small>Built by Chatbooks</small>
          </span>
        </div>
        <div className="auth-story-copy">
          <p className="eyebrow">Your friendly money workspace</p>
          <h1>Money talk should feel human.</h1>
          <p>
            Clear steps, plain words, and a careful review before anything changes. Your books stay
            rigorous underneath while the experience stays easy to follow.
          </p>
        </div>
        <div className="auth-character-stage">
          <div className="auth-character-bubble">We’ll make sense of it together.</div>
          <MoneyCompanion className="auth-companion" mood={registering ? "bright" : "curious"} />
          <span className="art-sticker art-sticker-safe">review first</span>
          <span className="art-sticker art-sticker-clear">plain words</span>
        </div>
        <div className="auth-assurance">
          <span>✓ Deterministic checks</span>
          <span>✓ Auditable history</span>
        </div>
      </section>
      <section className="auth-form-wrap">
        <form className="auth-form" onSubmit={submit}>
          <div className="auth-form-heading">
            <div className="auth-mini-greeting" aria-hidden="true">
              <CompanionMark />
            </div>
            <p className="eyebrow">
              {registering ? "Your money home starts here" : "Welcome back"}
            </p>
            <h2>{registering ? "Let’s get you set up." : "Ready for a clearer money day?"}</h2>
            <p>
              {registering
                ? "Create your account, then choose the business context you want to organize."
                : "Sign in to continue from where you left off."}
            </p>
          </div>
          {error && <Notice tone="error">{error}</Notice>}
          {registering && (
            <Field label="Your name">
              <input
                autoComplete="name"
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </Field>
          )}
          <Field label="Username or email">
            <input
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </Field>
          <Field label="Password" hint={registering ? "Use at least 12 characters." : undefined}>
            <input
              autoComplete={registering ? "new-password" : "current-password"}
              minLength={registering ? 12 : 1}
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <Button disabled={submitting || status === "loading"}>
            {submitting ? "Please wait…" : registering ? "Create account" : "Sign in"}
          </Button>
          <p className="auth-safety-note">
            Financial changes always wait for validation and review.
          </p>
          <p className="auth-switch">
            {registering ? "Already have an account?" : "New to Chatbooks?"}{" "}
            <Link href={registering ? "/login" : "/register"}>
              {registering ? "Sign in" : "Create one"}
            </Link>
          </p>
        </form>
      </section>
    </main>
  );
}
