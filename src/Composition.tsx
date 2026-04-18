import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";

export const TEMPLATE_FPS = 30;
export const TEMPLATE_DURATION_IN_FRAMES = TEMPLATE_FPS * 12;

export const MyComposition: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 18, TEMPLATE_DURATION_IN_FRAMES - 18, TEMPLATE_DURATION_IN_FRAMES], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [0, 18], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg, #0f172a 0%, #111827 48%, #1f2937 100%)",
        color: "#f8fafc",
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at top left, rgba(56,189,248,0.16), transparent 28%), radial-gradient(circle at bottom right, rgba(34,197,94,0.12), transparent 32%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 96,
          opacity,
          transform: `translateY(${translateY}px)`,
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: 1180,
            border: "1px solid rgba(248,250,252,0.14)",
            borderRadius: 32,
            padding: "56px 64px",
            background: "rgba(15,23,42,0.64)",
            boxShadow: "0 28px 80px rgba(0,0,0,0.28)",
            display: "flex",
            flexDirection: "column",
            gap: 24,
          }}
        >
          <div
            style={{
              fontSize: 18,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "rgba(248,250,252,0.72)",
            }}
          >
            Session-to-Video Template
          </div>
          <h1
            style={{
              margin: 0,
              fontSize: 72,
              lineHeight: 1.02,
            }}
          >
            Replace this template with your own shot-list-driven composition.
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: 30,
              lineHeight: 1.45,
              color: "rgba(248,250,252,0.88)",
              maxWidth: 980,
            }}
          >
            This repository now contains the reusable workflow, rules, and
            renderer scaffold only. Session-specific content, media, review
            outputs, and renders should live in the separate content directory.
          </p>
          <div
            style={{
              marginTop: 8,
              fontSize: 24,
              lineHeight: 1.5,
              color: "rgba(248,250,252,0.74)",
            }}
          >
            Start with the rules files, define a shot list, then generate
            review and render data from that source of truth.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
