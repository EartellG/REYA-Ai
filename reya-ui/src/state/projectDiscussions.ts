// src/state/projectDiscussions.ts
import { create } from "zustand";
import { nanoid } from "nanoid";

export type Role = "user" | "assistant";
export type Message = { id: string; role: Role; text: string; ts: number };
export type Thread = { id: string; title: string; archived: boolean; messages: Message[] };

type Store = {
  threads: Thread[];
  openThreadId: string | null;

  createThread: (title: string, firstMessage?: string) => string; // returns threadId
  openThread: (id: string) => void;
  addMessage: (id: string, role: Role, text: string) => void;
  archiveThread: (id: string) => void;
  deleteThread: (id: string) => void;
};

export const useProjectDiscussions = create<Store>((set, get) => ({
  threads: [],
  openThreadId: null,

  createThread: (title, firstMessage) => {
    const id = nanoid(8);
    const t: Thread = { id, title, archived: false, messages: [] };
    if (firstMessage) {
      t.messages.push({ id: nanoid(10), role: "user", text: firstMessage, ts: Date.now() });
    }
    set(s => ({ threads: [t, ...s.threads], openThreadId: id }));
    return id;
  },

  openThread: (id) => set({ openThreadId: id }),

  addMessage: (id, role, text) =>
    set(s => ({
      threads: s.threads.map(t =>
        t.id === id
          ? { ...t, messages: [...t.messages, { id: nanoid(10), role, text, ts: Date.now() }] }
          : t
      ),
    })),

  archiveThread: (id) =>
    set(s => ({ threads: s.threads.map(t => (t.id === id ? { ...t, archived: true } : t)) })),

  deleteThread: (id) =>
    set(s => ({
      threads: s.threads.filter(t => t.id !== id),
      openThreadId: s.openThreadId === id ? null : s.openThreadId,
    })),
}));
