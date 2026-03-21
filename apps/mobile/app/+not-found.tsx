import { useRouter } from "expo-router";

import { EmptyState } from "../src/components/EmptyState";
import { ScreenContainer } from "../src/components/ScreenContainer";

export default function NotFoundScreen() {
  const router = useRouter();
  return (
    <ScreenContainer>
      <EmptyState title="This screen does not exist" description="The route could not be found in the mobile app." actionLabel="Go home" onAction={() => router.replace("/")} />
    </ScreenContainer>
  );
}
