"use client";

import { useEffect, useRef, useState } from "react";

import { Icon } from "@/components/icons";

import { useFinancialSpace } from "./financial-space-provider";

export function ContextSwitcher() {
  const { space, organization, organizations, selectBusiness, selectPersonal } =
    useFinancialSpace();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function close(event: MouseEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", close);
    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", closeWithEscape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", closeWithEscape);
    };
  }, []);

  const contextName = space.kind === "personal" ? "Personal" : (organization?.name ?? "Business");
  return (
    <div className="context-switcher" ref={root}>
      <button
        className="context-trigger"
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className={`context-dot context-dot-${space.kind}`} />
        <span>
          <small>{space.kind === "personal" ? "Personal space" : "Business space"}</small>
          <strong>{contextName}</strong>
        </span>
        <Icon name="chevron" />
      </button>
      {open && (
        <div className="context-menu" role="menu" aria-label="Financial context">
          <p>Financial context</p>
          <button
            role="menuitemradio"
            aria-checked={space.kind === "personal"}
            onClick={() => {
              selectPersonal();
              setOpen(false);
            }}
          >
            <span className="context-dot context-dot-personal" />
            <span>
              <strong>Personal</strong>
              <small>Available in a future milestone</small>
            </span>
          </button>
          <div className="context-menu-label">Businesses</div>
          {organizations.map((item) => (
            <button
              key={item.id}
              role="menuitemradio"
              aria-checked={space.kind === "business" && organization?.id === item.id}
              onClick={() => {
                selectBusiness(item.id);
                setOpen(false);
              }}
            >
              <span className="context-dot context-dot-business" />
              <span>
                <strong>{item.name}</strong>
                <small>
                  {item.role.toLowerCase()} · {item.currency}
                </small>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
