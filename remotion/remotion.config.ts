import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');
Config.setOverwriteOutput(true);

// Enable GPU Acceleration for faster rendering
Config.setChromiumOpenGlRenderer('angle');

// Enable GPU Hardware Encoding (NVENC for NVIDIA RTX cards)
Config.setHardwareAcceleration('if-possible');
