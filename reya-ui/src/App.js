import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import reactLogo from "./assets/react.svg";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";
function App() {
    const [greetMsg, setGreetMsg] = useState("");
    const [name, setName] = useState("");
    async function greet() {
        // Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
        setGreetMsg(await invoke("greet", { name }));
    }
    return (_jsxs("main", { className: "container", children: [_jsx("h1", { children: "Welcome to Tauri + React" }), _jsxs("div", { className: "row", children: [_jsx("a", { href: "https://vitejs.dev", target: "_blank", children: _jsx("img", { src: "/vite.svg", className: "logo vite", alt: "Vite logo" }) }), _jsx("a", { href: "https://tauri.app", target: "_blank", children: _jsx("img", { src: "/tauri.svg", className: "logo tauri", alt: "Tauri logo" }) }), _jsx("a", { href: "https://reactjs.org", target: "_blank", children: _jsx("img", { src: reactLogo, className: "logo react", alt: "React logo" }) })] }), _jsx("p", { children: "Click on the Tauri, Vite, and React logos to learn more." }), _jsxs("form", { className: "row", onSubmit: (e) => {
                    e.preventDefault();
                    greet();
                }, children: [_jsx("input", { id: "greet-input", onChange: (e) => setName(e.currentTarget.value), placeholder: "Enter a name..." }), _jsx("button", { type: "submit", children: "Greet" })] }), _jsx("p", { children: greetMsg })] }));
}
export default App;
