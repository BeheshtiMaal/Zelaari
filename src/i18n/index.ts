import { fa } from "./fa";
import { en } from "./en";
export type Locale = "fa" | "en";
export type Dictionary = typeof fa;
export function dictionary(locale: Locale): Dictionary { return locale === "en" ? en : fa; }
