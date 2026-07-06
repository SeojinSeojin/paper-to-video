import { Config } from "@remotion/cli/config";

// Rendered frames are opaque, so JPEG keeps renders fast without visible loss.
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// H.264 in an MP4 container is what YouTube ingests happily.
Config.setCodec("h264");
