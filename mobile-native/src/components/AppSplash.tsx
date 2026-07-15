import { useEffect, useRef } from "react";
import { Animated, Image, StyleSheet, View } from "react-native";

const SPLASH_HOLD_MS = 1300;
const SPLASH_FADE_MS = 320;

interface AppSplashProps {
  onFinish: () => void;
}

export function AppSplash({ onFinish }: AppSplashProps) {
  const opacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const holdTimer = setTimeout(() => {
      Animated.timing(opacity, {
        toValue: 0,
        duration: SPLASH_FADE_MS,
        useNativeDriver: true,
      }).start(({ finished }) => {
        if (finished) onFinish();
      });
    }, SPLASH_HOLD_MS);

    return () => clearTimeout(holdTimer);
  }, [onFinish, opacity]);

  return (
    <Animated.View style={[styles.overlay, { opacity }]}>
      <View style={styles.canvas}>
        <Image
          source={require("../../assets/bada-splash.png")}
          resizeMode="contain"
          style={styles.image}
          accessibilityIgnoresInvertColors
        />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 999,
    elevation: 999,
    backgroundColor: "#FFFFFF",
  },
  canvas: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  image: {
    width: "100%",
    height: "100%",
  },
});
