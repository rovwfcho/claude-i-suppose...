#!/usr/bin/env bash
# Builds Egger Detector; the finished jar lands in OUTPUT/.
set -euo pipefail
cd "$(dirname "$0")"
for f in gradlew build.gradle settings.gradle gradle.properties gradle/wrapper/gradle-wrapper.jar gradle/wrapper/gradle-wrapper.properties \
         src/main/java/com/eggerdetector/Detector.java src/main/resources/fabric.mod.json; do
    [ -f "$f" ] || { echo "Missing file: $f - extract the whole zip first."; exit 1; }
done
JAVA_EXE=java
if [ -n "${JAVA_HOME:-}" ]; then JAVA_EXE="${JAVA_HOME//\"/}/bin/java"; fi
if ! "$JAVA_EXE" -version >/dev/null 2>&1; then
    echo "Java was not found. Install Java 25 (for example Eclipse Temurin 25) and run this again."; exit 1
fi
JV=$("$JAVA_EXE" -version 2>&1 | awk -F'"' '/version/ {print $2; exit}')
if [ "${JV%%.*}" -lt 25 ] 2>/dev/null; then
    echo "Found Java $JV - this build needs Java 25 or newer (set JAVA_HOME to a Java 25 folder)."; exit 1
fi
echo "Using Java $JV"
chmod +x gradlew
./gradlew clean build --no-daemon
mkdir -p OUTPUT
rm -f OUTPUT/eggerdetector-*.jar
BUILT=""
for j in build/libs/eggerdetector-*.jar; do
    case "$j" in *-sources.jar) continue ;; esac
    cp "$j" OUTPUT/ && BUILT=$(basename "$j")
done
[ -n "$BUILT" ] || { echo "The build finished but no jar was found in build/libs."; exit 1; }
echo "Done: OUTPUT/$BUILT"
echo "Put it in your .minecraft/mods folder with Fabric API (Mod Menu recommended). Cloth Config is already inside the jar."
