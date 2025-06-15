const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

export async function validateFile(file: File): Promise<{ is_valid: boolean; message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/validate`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error((await res.json()).detail || "Validation failed");
  }
  return res.json();
}

export async function convertFile(file: File, requestData?: object): Promise<{ downloadUrl: string }> {
  const formData = new FormData();
  formData.append("file", file);
  if (requestData) {
    formData.append("request_data", JSON.stringify(requestData));
  }

  const res = await fetch(`${API_BASE}/convert`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error((await res.json()).detail || "Conversion failed");
  }
  return res.json();
}