/// <reference types="vite/client" />

import type React from "react";
import type { HTMLPerspectiveViewerElement } from "@perspective-dev/viewer";

declare module "*.wasm?url" {
  const src: string;
  export default src;
}

type PerspectiveViewerProps = React.DetailedHTMLProps<
  React.HTMLAttributes<HTMLPerspectiveViewerElement> & {
    theme?: string;
    ref?: React.Ref<HTMLPerspectiveViewerElement>;
  },
  HTMLPerspectiveViewerElement
>;

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "perspective-viewer": PerspectiveViewerProps;
    }
  }
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      "perspective-viewer": PerspectiveViewerProps;
    }
  }
}
