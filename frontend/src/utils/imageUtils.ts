const MAX_EDGE = 1024;

export type PendingImage = {
  base64: string;
  mediaType: string;
  previewUrl: string;
};

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("读取图片失败"));
    reader.readAsDataURL(file);
  });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("图片加载失败"));
    img.src = src;
  });
}

/** 压缩最长边，返回 base64（无 data: 前缀）与 MIME。 */
export async function prepareImageFile(file: File): Promise<PendingImage> {
  if (!file.type.startsWith("image/")) {
    throw new Error("仅支持图片文件");
  }
  const dataUrl = await readFileAsDataUrl(file);
  const img = await loadImage(dataUrl);

  let { width, height } = img;
  const maxEdge = Math.max(width, height);
  if (maxEdge > MAX_EDGE) {
    const scale = MAX_EDGE / maxEdge;
    width = Math.round(width * scale);
    height = Math.round(height * scale);
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("无法处理图片");
  }
  ctx.drawImage(img, 0, 0, width, height);

  const mediaType = file.type === "image/png" ? "image/png" : "image/jpeg";
  const outUrl = canvas.toDataURL(mediaType, 0.92);
  const base64 = outUrl.split(",", 2)[1] ?? "";
  if (!base64) {
    throw new Error("图片编码失败");
  }
  return { base64, mediaType, previewUrl: outUrl };
}

export async function prepareImageFromClipboard(items: DataTransferItemList): Promise<PendingImage | null> {
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) {
        return prepareImageFile(file);
      }
    }
  }
  return null;
}
