"use client"; // Need this for useState and useEffect

import { useState, FormEvent } from "react";

export default function Home() {
  const [message, setMessage] = useState<string>("");
  const [streamedResponse, setStreamedResponse] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    setIsLoading(true);
    setStreamedResponse([]); // Clear previous responses
    setError(null);

    try {
      // NOTE: We are sending to /api/agent_chat, assuming a Next.js API route
      // will be set up later to proxy requests to the actual FastAPI backend
      // running on port 8000 to avoid CORS issues in the browser.
      const response = await fetch("/api/agent_chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      // Process the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulatedText = ""; // Accumulate text here

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");

        // Keep the last potentially incomplete line in the buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim()) {
            try {
              // Attempt to parse the simple {"text": "..."} JSON
              const parsedChunk = JSON.parse(line);
              if (parsedChunk && typeof parsedChunk.text === 'string') {
                // Append the text to our accumulated string
                accumulatedText += parsedChunk.text;
                // Update the state with the accumulated text as a single item for display
                // Alternatively, you could keep adding chunks if you want to show the raw stream
                setStreamedResponse([accumulatedText]);
              } else {
                // Handle unexpected JSON structure if needed
                 console.warn("Received chunk without expected 'text' field:", parsedChunk);
              }

            } catch (parseError) {
              console.error("Failed to parse stream chunk:", line, parseError);
              // If parsing fails, it's likely not our simple text JSON
              // Optionally display raw line or ignore
              // setStreamedResponse((prev) => [...prev, `[RAW] ${line}`]);
            }
          }
        }
      }
      // Process any remaining data in the buffer - might be the last part of text
      if (buffer.trim()) {
         try {
           const parsedChunk = JSON.parse(buffer);
             if (parsedChunk && typeof parsedChunk.text === 'string') {
               accumulatedText += parsedChunk.text;
               setStreamedResponse([accumulatedText]);
             }
         } catch (parseError) {
            console.error("Failed to parse final stream chunk:", buffer, parseError);
         }
      }


    } catch (err: any) {
      console.error("Error fetching stream:", err);
      setError(err.message || "An unknown error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-12 bg-gray-50">
      <h1 className="text-3xl font-bold mb-8 text-gray-800">Aspen Agent Chat</h1>

      <form onSubmit={handleSubmit} className="w-full max-w-2xl mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter your message..."
            className="flex-grow p-3 border text-black border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Sending..." : "Send"}
          </button>
        </div>
      </form>

      {error && (
        <div className="w-full max-w-2xl p-4 mb-4 text-red-700 bg-red-100 border border-red-400 rounded-lg">
          Error: {error}
        </div>
      )}

      <div className="w-full max-w-2xl bg-white p-4 border border-gray-200 rounded-lg shadow space-y-2 h-[60vh] overflow-y-auto">
        <h2 className="text-xl font-semibold mb-2 text-gray-700">Agent Response:</h2>
        {streamedResponse.length === 0 && !isLoading && (
          <p className="text-gray-500 italic">No response yet...</p>
        )}
        {streamedResponse.map((fullText, index) => (
          <pre
            key={index}
            className="p-2 bg-gray-100 border border-gray-200 rounded text-sm text-gray-800 overflow-x-auto whitespace-pre-wrap break-words"
          >
            {fullText}
          </pre>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-500 italic pt-2">
            <span>Agent is thinking</span>
            <span className="animate-bounce">...</span>
          </div>
        )}
      </div>
    </main>
  );
}
