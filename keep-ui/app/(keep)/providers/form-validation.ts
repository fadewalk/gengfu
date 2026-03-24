import { z } from "zod";
import { Provider } from "@/shared/api/providers";

type URLOptions = {
  protocols: string[];
  requireTld: boolean;
  requireProtocol: boolean;
  requirePort: boolean;
  alllowMultihost: boolean;
  validateLength: boolean;
  maxLength: number;
};

type ValidatorRes = { success: true } | { success: false; msg: string };

const defaultURLOptions: URLOptions = {
  protocols: [],
  requireTld: false,
  requireProtocol: true,
  requirePort: false,
  alllowMultihost: false,
  validateLength: true,
  maxLength: 2 ** 16,
};

function mergeOptions<T extends Record<string, unknown>>(
  defaults: T,
  opts?: Partial<T>
): T {
  if (!opts) return defaults;
  return { ...defaults, ...opts };
}

type TranslateFn = (key: string, params?: Record<string, string>) => string;

const error = (msg: string) => ({ success: false, msg });
const fallback = (msg: string) => msg;

const urlError = (t: TranslateFn) => error(t("providers.validation.validUrl", undefined) ?? fallback("Please provide a valid URL"));
const protocolError = (t: TranslateFn) => error(t("providers.validation.validUrlProtocol", undefined) ?? fallback("A valid URL protocol is required"));
const relProtocolError = (t: TranslateFn) => error(t("providers.validation.relativeUrlNotAllowed", undefined) ?? fallback("A protocol-relative URL is not allowed"));
const multiProtocolError = (t: TranslateFn) => error(t("providers.validation.multiProtocolNotAllowed", undefined) ?? fallback("URL cannot have more than one protocol"));
const missingPortError = (t: TranslateFn) => error(t("providers.validation.portRequired", undefined) ?? fallback("A URL with a port number is required"));
const portError = (t: TranslateFn) => error(t("providers.validation.invalidPortNumber", undefined) ?? fallback("Invalid port number"));
const hostError = (t: TranslateFn) => error(t("providers.validation.invalidHost", undefined) ?? fallback("Invalid URL host"));
const hostWildcardError = (t: TranslateFn) => error(t("providers.validation.wildcardHostNotAllowed", undefined) ?? fallback("Wildcard in URL host is not allowed"));
const multihostError = (t: TranslateFn) => error(t("providers.validation.multiHostNotAllowed", undefined) ?? fallback("Multiple hosts are not allowed"));
const multihostProtocolError = (t: TranslateFn) => error(t("providers.validation.invalidMultiHostProtocol", undefined) ?? fallback("Invalid multihost protocol"));
const tldError = (t: TranslateFn) => error(t("providers.validation.validTldRequired", undefined) ?? fallback("URL must contain a valid TLD e.g .com, .io, .dev, .net"));

function getProtocolError(protocols: URLOptions["protocols"], t: TranslateFn) {
  if (protocols.length === 0) return protocolError(t);
  if (protocols.length === 1)
    return error(t("providers.validation.protocolRequired", { protocol: protocols[0] }) ?? `A URL with \`${protocols[0]}\` protocol is required`);
  if (protocols.length === 2)
    return error(
      t("providers.validation.protocolOrRequired", { protocol1: protocols[0], protocol2: protocols[1] }) ?? `A URL with \`${protocols[0]}\` or \`${protocols[1]}\` protocol is required`
    );
  const lst = protocols.length - 1;
  const wrap = (acc: string, p: string) => acc + `\`${p}\``;
  const optsStr = protocols.reduce(
    (acc, p, i) =>
      i === lst
        ? wrap(acc, p)
        : i === lst - 1
          ? wrap(acc, p) + " or "
          : wrap(acc, p) + ", ",
    ""
  );
  return error(t("providers.validation.oneOfProtocolsRequired", { protocols: optsStr }) ?? `A URL with one of ${optsStr} protocols is required`);
}

function isFQDN(str: string, options?: Partial<URLOptions>, t?: TranslateFn): ValidatorRes {
  const opts = mergeOptions(defaultURLOptions, options);

  if (str[str.length - 1] === ".") return hostError(t ?? fallback); // trailing dot not allowed
  if (str.indexOf("*.") === 0) return hostWildcardError(t ?? fallback); // wildcard not allowed

  const parts = str.split(".");
  const tld = parts[parts.length - 1];
  const tldRegex =
    /^([a-z\u00A1-\u00A8\u00AA-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]{2,}|xn[a-z0-9-]{2,})$/i;

  if (
    opts.requireTld &&
    (parts.length < 2 || !tldRegex.test(tld) || /\s/.test(tld))
  )
    return tldError(t ?? fallback);

  const partsValid = parts.every((part) => {
    if (!/^[a-z_\u00a1-\uffff0-9-]+$/i.test(part)) {
      return false;
    }

    // disallow full-width chars
    if (/[\uff01-\uff5e]/.test(part)) {
      return false;
    }

    // disallow parts starting or ending with hyphen
    if (/^-|-$/.test(part)) {
      return false;
    }

    return true;
  });

  return partsValid ? { success: true } : hostError(t ?? fallback);
}

function isIP(str: string) {
  const validation = z.string().ip().safeParse(str);
  return validation.success;
}

function validateHost(hostname: string, opts: URLOptions, t?: TranslateFn): ValidatorRes {
  let host: string;
  let port: number;
  let portStr: string = "";
  let split: string[];

  // extract ipv6 & port
  const wrapped_ipv6 = /^\[([^\]]+)\](?::([0-9]+))?$/;
  const ipv6Match = hostname.match(wrapped_ipv6);
  if (ipv6Match) {
    host = ipv6Match[1];
    portStr = ipv6Match[2];
  } else {
    split = hostname.split(":");
    host = split.shift() ?? "";
    if (split.length) portStr = split.join(":");
  }

  if (portStr.length) {
    port = parseInt(portStr, 10);
    if (Number.isNaN(port)) return urlError(t ?? fallback);
    if (port <= 0 || port > 65_535) return portError(t ?? fallback);
  } else if (opts.requirePort) return missingPortError(t ?? fallback);

  if (!host) return hostError(t ?? fallback);
  if (isIP(host)) return { success: true };
  return isFQDN(host, opts, t);
}

function isURL(str: string, options?: Partial<URLOptions>, t?: TranslateFn): ValidatorRes {
  const opts = mergeOptions(defaultURLOptions, options);

  if (str.length === 0 || /[\s<>]/.test(str)) return urlError(t ?? fallback);
  if (opts.validateLength && str.length > opts.maxLength) {
    const msg = t ? t("providers.validation.urlMaxLength", { max: String(opts.maxLength) }) : `Invalid url length, max of ${opts.maxLength} expected.`;
    return error(msg);
  }

  let url = str;
  let split: string[];

  split = url.split("#");
  url = split.shift() ?? "";

  split = url.split("?");
  url = split.shift() ?? "";

  if (url.slice(0, 2) === "//") return relProtocolError(t ?? fallback);

  // extract protocol & validate
  split = url.split("://");
  if (split.length > 2) return multiProtocolError(t ?? fallback);
  if (split.length > 1) {
    const protocol = split.shift()?.toLowerCase() ?? "";
    if (opts.protocols.length && opts.protocols.indexOf(protocol) === -1)
      return getProtocolError(opts.protocols, t ?? fallback);
    if (protocol.includes(",")) return multihostProtocolError(t ?? fallback);
    url = split.join("://");
  } else if (opts.requireProtocol) {
    return getProtocolError(opts.protocols, t ?? fallback);
  }

  split = url.split("/");
  url = split.shift() ?? "";
  if (!url.length) return urlError(t ?? fallback);

  // extract auth details & validate
  split = url.split("@");
  if (split.length > 1 && !split[0]) return urlError(t ?? fallback);
  if (split.length > 1) {
    const auth = split.shift() ?? "";
    if (auth.split(":").length > 2) return urlError(t ?? fallback);
    const [user, pass] = auth.split(":");
    if (!user && !pass) return urlError(t ?? fallback);
  }
  const hostname = split.join("@");

  // validate multihost
  split = hostname.split(",");
  if (split.length > 1 && !opts.alllowMultihost) return multihostError(t ?? fallback);
  if (split.length > 1) {
    for (const host of split) {
      const res = validateHost(host, opts, t);
      if (!res.success) return res;
    }
    return { success: true };
  }
  return validateHost(hostname, opts, t);
}

function getBaseUrlSchema(options?: Partial<URLOptions>, required_error?: string, t?: TranslateFn) {
  const urlStr = z.string({ required_error: required_error ?? "This field is required" });
  const schema = urlStr.superRefine((url, ctx) => {
    const valdn = isURL(url, options, t);
    if (valdn.success) return;
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: valdn.msg,
    });
  });
  return schema;
}

export function getZodSchema(fields: Provider["config"], installed: boolean, t?: (key: string, ...args: any[]) => string) {
  const required_error = t ? t("providers.validation.required") : "This field is required";
  const portError = t ? t("providers.validation.invalidPort") : "Invalid port number";
  const translateFn: TranslateFn | undefined = t;

  const kvPairs = Object.entries(fields).map(([field, config]) => {
    if (config.type === "form") {
      const baseSchema = z.record(z.string(), z.string()).array();
      const schema = config.required
        ? baseSchema.nonempty({
            message: t ? t("providers.validation.atLeastOneEntry") : "At least one key-value entry should be provided.",
          })
        : baseSchema.optional();
      return [field, schema];
    }

    if (config.type === "file") {
      const baseSchema = z
        .instanceof(File, { message: t ? t("providers.validation.uploadFile") : "Please upload a file here." })
        .or(z.string())
        .refine(
          (file) => {
            if (config.file_type == undefined) return true;
            if (config.file_type.length <= 1) return true;
            if (typeof file === "string" && installed) return true;
            return (
              typeof file !== "string" && config.file_type.includes(file.type)
            );
          },
          {
            message:
              config.file_type && config.file_type?.split(",").length > 1
                ? (t ? t("providers.validation.fileTypeOneOf", { types: config.file_type }) : `File type should be one of ${config.file_type}.`)
                : (t ? t("providers.validation.fileType", { type: config.file_type }) : `File should be of type ${config.file_type}.`),
          }
        );
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.type === "switch") {
      const schema = config.required ? z.boolean() : z.boolean().optional();
      return [field, schema];
    }

    if (config.validation === "any_url") {
      const baseSchema = getBaseUrlSchema(undefined, required_error, translateFn);
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.validation === "any_http_url") {
      const baseSchema = getBaseUrlSchema({ protocols: ["http", "https"] }, required_error, translateFn);
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.validation === "https_url") {
      const baseSchema = getBaseUrlSchema({
        protocols: ["https"],
        requireTld: true,
        maxLength: 2083,
      }, required_error, translateFn);
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.validation === "no_scheme_url") {
      const baseSchema = getBaseUrlSchema({ requireProtocol: false }, required_error, translateFn);
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.validation === "multihost_url") {
      const baseSchema = getBaseUrlSchema({ alllowMultihost: true }, required_error, translateFn);
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.validation === "no_scheme_multihost_url") {
      const baseSchema = getBaseUrlSchema({
        alllowMultihost: true,
        requireProtocol: false,
      }, required_error, translateFn);
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.validation === "tld") {
      const baseSchema = z
        .string({ required_error })
        .regex(new RegExp(/\.[a-z]{2,63}$/), {
          message: t ? t("providers.validation.validTLD") : "Please provide a valid TLD e.g .com, .io, .dev, .net",
        });
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }

    if (config.validation === "port") {
      const baseSchema = z
        .string({ required_error })
        .pipe(
          z.coerce
            .number({ invalid_type_error: portError })
            .min(1, { message: portError })
            .max(65_535, { message: portError })
        );
      const schema = config.required ? baseSchema : baseSchema.optional();
      return [field, schema];
    }
    return [
      field,
      config.required
        ? z
            .string({ required_error })
            .trim()
            .min(1, { message: required_error })
        : z.string().optional(),
    ];
  });
  return z.object({
    provider_name: z
      .string({ required_error })
      .trim()
      .min(1, { message: required_error }),
    ...Object.fromEntries(kvPairs),
  });
}
