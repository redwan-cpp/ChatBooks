type CompanionMood = "bright" | "curious";

function classes(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function CompanionMark({ className }: { className?: string }) {
  return (
    <span className={classes("companion-mark", className)} aria-hidden="true">
      <span className="companion-mark-face">
        <i />
        <i />
      </span>
      <span className="companion-mark-leaf" />
    </span>
  );
}

export function MoneyCompanion({
  className,
  mood = "bright",
}: {
  className?: string;
  mood?: CompanionMood;
}) {
  return (
    <svg
      className={classes("money-companion", `money-companion-${mood}`, className)}
      aria-hidden="true"
      viewBox="0 0 360 330"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="companion-body" x1="75" y1="58" x2="263" y2="276">
          <stop stopColor="#7FE9A9" />
          <stop offset="0.55" stopColor="#34C989" />
          <stop offset="1" stopColor="#1B9D70" />
        </linearGradient>
        <linearGradient id="companion-card" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#FFFDF4" />
          <stop offset="1" stopColor="#E9F8DA" />
        </linearGradient>
        <filter id="companion-shadow" x="20" y="28" width="310" height="294">
          <feDropShadow dx="0" dy="14" stdDeviation="12" floodColor="#063E30" floodOpacity="0.25" />
        </filter>
      </defs>

      <ellipse cx="181" cy="296" rx="112" ry="18" fill="#082F26" opacity="0.18" />
      <g className="companion-sparkles">
        <path
          d="M53 94c14-1 22-9 24-23 2 14 9 22 23 24-14 2-22 9-24 23-2-14-9-22-23-24Z"
          fill="#FFE174"
        />
        <path
          d="M278 73c9-1 14-6 15-15 2 9 7 14 16 15-9 2-14 7-15 16-2-9-7-14-16-16Z"
          fill="#FF8E7A"
        />
        <circle cx="318" cy="130" r="10" fill="#A78BFA" />
        <circle cx="47" cy="169" r="7" fill="#A78BFA" />
      </g>

      <g filter="url(#companion-shadow)">
        <path
          d="M176 45c52-2 94 21 116 67 22 46 16 105-17 143-25 29-67 45-111 40-47-5-86-28-105-65-20-38-20-91 3-128 25-39 65-55 114-57Z"
          fill="url(#companion-body)"
        />
        <path d="M164 47c-5-22 8-37 30-40 1 20-8 34-30 40Z" fill="#B9F15D" />
        <path d="M162 47c-23-3-35-18-32-39 21 3 33 16 32 39Z" fill="#5BDD9B" />
        <path
          d="M76 198c-19 5-33 18-38 38 22 2 39-7 50-26"
          fill="#32BE82"
          stroke="#147A58"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <path
          d="M277 193c21 4 36 17 42 37-23 4-42-5-54-25"
          fill="#32BE82"
          stroke="#147A58"
          strokeWidth="6"
          strokeLinecap="round"
        />
      </g>

      <g className="companion-face">
        <ellipse cx="135" cy="139" rx="34" ry="40" fill="#FFFDF5" />
        <ellipse cx="218" cy="139" rx="34" ry="40" fill="#FFFDF5" />
        <ellipse cx="143" cy="149" rx="14" ry="20" fill="#153C31" />
        <ellipse cx="210" cy="149" rx="14" ry="20" fill="#153C31" />
        <circle cx="148" cy="141" r="5" fill="white" />
        <circle cx="215" cy="141" r="5" fill="white" />
        {mood === "curious" ? (
          <>
            <path
              d="M111 102c14-10 28-10 42-1"
              stroke="#147A58"
              strokeWidth="8"
              strokeLinecap="round"
            />
            <path
              d="M197 99c15-6 29-3 40 8"
              stroke="#147A58"
              strokeWidth="8"
              strokeLinecap="round"
            />
          </>
        ) : (
          <>
            <path
              d="M111 105c14-9 28-9 42 0"
              stroke="#147A58"
              strokeWidth="8"
              strokeLinecap="round"
            />
            <path
              d="M199 105c14-9 28-9 42 0"
              stroke="#147A58"
              strokeWidth="8"
              strokeLinecap="round"
            />
          </>
        )}
        <path
          d="M151 190c14 15 34 15 49 0"
          stroke="#0D684D"
          strokeWidth="8"
          strokeLinecap="round"
        />
        <path d="M162 203c8 5 18 5 27 0" stroke="#FF8E7A" strokeWidth="5" strokeLinecap="round" />
        <ellipse cx="101" cy="181" rx="17" ry="9" fill="#A8F0C2" opacity="0.65" />
        <ellipse cx="251" cy="181" rx="17" ry="9" fill="#A8F0C2" opacity="0.65" />
      </g>

      <g className="companion-ledger" transform="rotate(-4 180 245)">
        <rect
          x="114"
          y="218"
          width="132"
          height="80"
          rx="18"
          fill="url(#companion-card)"
          stroke="#0D684D"
          strokeWidth="6"
        />
        <rect x="130" y="235" width="39" height="10" rx="5" fill="#A78BFA" />
        <path
          d="M130 258h100M130 276h100M183 251v34"
          stroke="#58B889"
          strokeWidth="5"
          strokeLinecap="round"
        />
        <circle cx="219" cy="240" r="7" fill="#FFE174" />
      </g>
    </svg>
  );
}
