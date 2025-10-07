"use client";

import { useState, useEffect } from "react";
import { PipecatAppBase } from "@pipecat-ai/voice-ui-kit";

import { ClientApp } from "./ClientApp";

import "@pipecat-ai/voice-ui-kit/styles.scoped";

const connectUrl = process.env.NEXT_PUBLIC_DAILY_ROOM_URL;

export default function Home() {
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile devices
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(
        /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
          navigator.userAgent
        )
      );
    };
    checkMobile();
  }, []);

  return (
    <div className="vkui-root">
      <div className="voice-ui-kit">
        <PipecatAppBase
          transportType="daily"
          connectParams={
            Boolean(connectUrl)
              ? {
                  room_url: connectUrl,
                }
              : undefined
          }
          startBotParams={
            Boolean(connectUrl)
              ? undefined
              : {
                  endpoint: "/api/start",
                }
          }
          startBotResponseTransformer={
            connectUrl
              ? undefined
              : // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (response: any) => {
                  return {
                    room_url: response.dailyRoom,
                    token: response.dailyToken,
                  };
                }
          }
        >
          {({ handleConnect, handleDisconnect }) => (
            <ClientApp
              connect={handleConnect}
              disconnect={handleDisconnect}
              isMobile={isMobile}
            />
          )}
        </PipecatAppBase>
      </div>
    </div>
  );
}
