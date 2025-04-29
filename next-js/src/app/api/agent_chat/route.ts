import { type NextRequest } from 'next/server';

// Define the backend URL (your FastAPI server)
const BACKEND_URL = 'http://127.0.0.1:8000/agent_chat';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json(); // Get the message from the frontend request

    // Forward the request to the FastAPI backend
    const backendResponse = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add any other headers if needed, like authentication tokens
      },
      body: JSON.stringify(body), // Forward the original body
    });

    // Check if the backend request was successful
    if (!backendResponse.ok) {
      // Forward the backend's error status and message if possible
      const errorText = await backendResponse.text();
      return new Response(`Backend Error: ${errorText}`, {
        status: backendResponse.status,
      });
    }

    // Check if the backend response includes a body to stream
    if (!backendResponse.body) {
      return new Response('Backend response body is null', { status: 500 });
    }

    // Create a ReadableStream to pipe the backend stream
    const stream = new ReadableStream({
      async start(controller) {
        if (!backendResponse.body) {
          controller.close();
          return;
        }
        const reader = backendResponse.body.getReader();

        function push() {
          reader.read().then(({ done, value }) => {
            if (done) {
              console.log('Proxy stream finished.');
              controller.close();
              return;
            }
            // Push the chunk from the backend to the frontend client
            controller.enqueue(value);
            push(); // Continue reading
          }).catch(err => {
            console.error('Error reading from backend stream:', err);
            controller.error(err);
          });
        }

        push();
      }
    });

    // Return the stream to the frontend client
    // Set appropriate headers for streaming
    return new Response(stream, {
      headers: {
        'Content-Type': 'application/x-ndjson', // Match backend stream type
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error: any) {
    console.error('Error in API proxy route:', error);
    return new Response(`Internal Server Error: ${error.message}`, { status: 500 });
  }
} 