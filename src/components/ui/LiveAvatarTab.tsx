import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

export default function LiveAvatarTab() {
  const [avatarSpeaking, setAvatarSpeaking] = useState(false);
  const [spokenText, setSpokenText] = useState("");

  // Simulate avatar speaking
  const simulateSpeak = async () => {
    const text = "Hello, I'm REYA.";
    setSpokenText(text);
    setAvatarSpeaking(true);
    speakText(text);
  };

  const speakText = (text: string) => {
    const synth = window.speechSynthesis;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onend = () => setAvatarSpeaking(false);
    synth.speak(utterance);
  };

  return (
    <div className="p-6 text-center">
      <h2 className="text-2xl font-bold mb-4">👄 Live Avatar Mode</h2>
      <img
        src="/REYA_Avatar.png"
        alt="REYA Avatar"
        className={`mx-auto h-48 transition-transform ${
          avatarSpeaking ? "animate-pulse scale-105" : ""
        }`}
      />
      <p className="mt-4 text-gray-400 italic">{spokenText}</p>
      <Button className="mt-6" onClick={simulateSpeak}>
        🔊 Speak Test Line
      </Button>
    </div>
  );
}
