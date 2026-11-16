import { createBrowserClient } from "@supabase/ssr";

// Cliente del navegador. Las variables NEXT_PUBLIC_ se incrustan al compilar.
export function createClient() {
  return createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!);
}
