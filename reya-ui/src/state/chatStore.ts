import { create } from "zustand";

export type ChatMsg = { id: string; role: "user" | "assistant"; text: string; ts: number };

type ChatState = {
  messages: ChatMsg[];
  add: (m: ChatMsg) => void;
  addUser: (text: string) => void;
  addAssistant: (text: string) => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  add: (m) => set((s) => ({ messages: [...s.messages, m] })),
  addUser: (text) =>
    set((s) => ({ messages: [...s.messages, { id: crypto.randomUUID(), role: "user", text, ts: Date.now() }] })),
  addAssistant: (text) =>
    set((s) => ({ messages: [...s.messages, { id: crypto.randomUUID(), role: "assistant", text, ts: Date.now() }] })),
}));
