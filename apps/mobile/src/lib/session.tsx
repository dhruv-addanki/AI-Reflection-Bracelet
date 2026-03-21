import type { ReactNode } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { Device, UserProfile } from "@bracelet/shared-types";
import { createContext, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "bracelet-session";

type SessionState = {
  hydrated: boolean;
  user: UserProfile | null;
  device: Device | null;
  setUser: (user: UserProfile | null) => Promise<void>;
  setDevice: (device: Device | null) => Promise<void>;
  applySeededDemo: (user: UserProfile, device: Device) => Promise<void>;
  clear: () => Promise<void>;
};

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false);
  const [user, setUserState] = useState<UserProfile | null>(null);
  const [device, setDeviceState] = useState<Device | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((value) => {
        if (!value) {
          return;
        }
        const parsed = JSON.parse(value) as { user: UserProfile | null; device: Device | null };
        setUserState(parsed.user);
        setDeviceState(parsed.device);
      })
      .finally(() => setHydrated(true));
  }, []);

  async function persist(nextUser: UserProfile | null, nextDevice: Device | null) {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({ user: nextUser, device: nextDevice }));
    setUserState(nextUser);
    setDeviceState(nextDevice);
  }

  return (
    <SessionContext.Provider
      value={{
        hydrated,
        user,
        device,
        setUser: async (nextUser) => persist(nextUser, device),
        setDevice: async (nextDevice) => persist(user, nextDevice),
        applySeededDemo: async (nextUser, nextDevice) => persist(nextUser, nextDevice),
        clear: async () => {
          await AsyncStorage.removeItem(STORAGE_KEY);
          setUserState(null);
          setDeviceState(null);
        }
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return context;
}
