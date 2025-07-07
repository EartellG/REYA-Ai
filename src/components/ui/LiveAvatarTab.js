import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Button } from "@/components/ui/button";
export default function LiveAvatarTab() {
    const [avatarSpeaking, setAvatarSpeaking] = useState(false);
    const [spokenText, setSpokenText] = useState("");
    // Simulate avatar speaking
    const simulateSpeak = async () => {
        const text = "Hello, I'm REYA. How can I assist you today?";
        setSpokenText(text);
        setAvatarSpeaking(true);
        speakText(text);
    };
    const speakText = (text) => {
        const synth = window.speechSynthesis;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.onend = () => setAvatarSpeaking(false);
        synth.speak(utterance);
    };
    return (_jsxs("div", { className: "p-6 text-center", children: [_jsx("h2", { className: "text-2xl font-bold mb-4", children: "\uD83D\uDC44 Live Avatar Mode" }), _jsx("img", { src: "/ReyaAva.png", alt: "REYA Avatar", className: `mx-auto h-48 transition-transform ${avatarSpeaking ? "animate-pulse scale-105" : ""}` }), _jsx("p", { className: "mt-4 text-gray-400 italic", children: spokenText }), _jsx(Button, { className: "mt-6", onClick: simulateSpeak, children: "\uD83D\uDD0A Speak Test Line" })] }));
}
