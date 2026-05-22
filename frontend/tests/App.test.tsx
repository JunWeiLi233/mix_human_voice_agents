import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../src/App";

describe("App", () => {
  it("renders the mixed voice studio", () => {
    render(<App />);
    expect(screen.getByText("Mixed Voice Agent Studio")).toBeInTheDocument();
    expect(screen.getByText("Voice Library")).toBeInTheDocument();
    expect(screen.getByText("Blend Mixer")).toBeInTheDocument();
    expect(screen.getByText("Agent Provider")).toBeInTheDocument();
    expect(screen.getByText("Voice Engine")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Qwen3-TTS" })).toBeInTheDocument();
    expect(screen.getByText("No imported voices yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create blend from imported voices" })).toBeDisabled();
  });
});
