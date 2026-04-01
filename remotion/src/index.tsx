import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {PodcastClip} from './PodcastClip';
import type {RenderConfig} from './types';

const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="PodcastClip"
      component={PodcastClip}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        renderConfig: null as RenderConfig | null,
      }}
    />
  );
};

registerRoot(RemotionRoot);
