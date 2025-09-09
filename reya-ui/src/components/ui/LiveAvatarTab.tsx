import { useState } from "react";
import { Button } from "@/components/ui/button";
import { playReyaTTS } from "@/lib/reyaTts";

export default function LiveAvatarTab() {
  const [avatarSpeaking, setAvatarSpeaking] = useState(false);
  const [spokenText, setSpokenText] = useState("");

  const simulateSpeak = async () => {
    const text = "Hello, I'm REYA.";
    setSpokenText(text);
    setAvatarSpeaking(true);

    const audio = await playReyaTTS(text);
    if (!audio) {
      setAvatarSpeaking(false);
      return;
    }

    console.log("LiveAvatar audio src:", audio.src); // should be /static/audio/....mp3
    audio.onended = () => setAvatarSpeaking(false);
    audio.onpause = () => setAvatarSpeaking(false);
    audio.onerror = () => setAvatarSpeaking(false);
  };

  return (
    <div className="p-6 text-center">
      <h2 className="text-2xl font-bold mb-4">👄 Live Avatar Mode</h2>
      <img
        src="/ReyaAva.png"
        alt="REYA Avatar"
        className={`mx-auto h-55 w-52 object-cover rounded-full transition-transform ${
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
