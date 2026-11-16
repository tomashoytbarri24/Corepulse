import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/supabase/env";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/cuenta", "/auth", "/api", "/logout"] },
    sitemap: `${siteUrl()}/sitemap.xml`,
  };
}
