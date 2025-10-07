import { NextResponse } from "next/server";

export async function POST() {
  const startUrl = process.env.PCC_START_URL;
  const apiToken = process.env.PCC_API_KEY;

  if (!startUrl || !apiToken) {
    return NextResponse.json(
      { error: "Missing PCC_START_URL or PCC_API_KEY env vars" },
      { status: 500 }
    );
  }

  try {
    const response = await fetch(startUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiToken}`,
      },
      body: JSON.stringify({ createDailyRoom: true }),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to start agent", details: data },
        { status: response.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: "Request failed", message },
      { status: 500 }
    );
  }
}


