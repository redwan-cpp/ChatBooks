import type { SVGProps } from "react";

export type IconName =
  | "activity"
  | "arrow"
  | "attachment"
  | "chat"
  | "check"
  | "chevron"
  | "close"
  | "menu"
  | "money"
  | "more"
  | "plus"
  | "projects"
  | "reports"
  | "retry"
  | "send"
  | "settings"
  | "shield"
  | "user";

const paths: Record<IconName, React.ReactNode> = {
  activity: <path d="M4 17h3l2-6 3 9 2-7 2 4h4" />,
  arrow: <path d="m9 18 6-6-6-6" />,
  attachment: <path d="m8.5 12.5 6-6a3 3 0 0 1 4.2 4.2l-8 8a5 5 0 0 1-7.1-7.1l8-8" />,
  chat: <path d="M20 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4Z" />,
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m7 10 5 5 5-5" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  money: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 9h.01M17 15h.01M8 12h8" />
    </>
  ),
  more: (
    <>
      <circle cx="5" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  projects: (
    <>
      <path d="M4 7h6l2 2h8v10H4Z" />
      <path d="M4 7V5h6l2 2" />
    </>
  ),
  reports: (
    <>
      <path d="M5 20V10M12 20V4M19 20v-7" />
    </>
  ),
  retry: (
    <>
      <path d="M20 7v5h-5" />
      <path d="M18 17a8 8 0 1 1 1.4-8" />
    </>
  ),
  send: <path d="m4 4 17 8-17 8 3-8Zm3 8h14" />,
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" />
    </>
  ),
  shield: <path d="M12 3 5 6v5c0 4.4 2.8 8.2 7 10 4.2-1.8 7-5.6 7-10V6Zm-3 9 2 2 4-5" />,
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
};

export function Icon({ name, ...props }: { name: IconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
      {...props}
    >
      {paths[name]}
    </svg>
  );
}
