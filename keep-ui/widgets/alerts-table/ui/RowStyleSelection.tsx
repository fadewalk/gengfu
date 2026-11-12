import React from "react";
import { Text } from "@tremor/react";
import {
  RowStyle,
  useAlertRowStyle,
} from "@/entities/alerts/model/useAlertRowStyle";
import { useI18n } from "@/i18n/hooks/useI18n";
interface RowStyleSelectionProps {
  onClose?: () => void;
}

export function RowStyleSelection({ onClose }: RowStyleSelectionProps) {
  const { t } = useI18n();
  const [rowStyle, setRowStyle] = useAlertRowStyle();

  const handleStyleChange = (style: RowStyle) => {
    setRowStyle(style);
    onClose?.();
  };

  return (
    <form className="flex flex-col h-full">
      <div className="flex-1 overflow-hidden flex flex-col">
        <span className="text-gray-400 text-sm mb-2">{t("alerts.rowDensity.title")}</span>
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => handleStyleChange("default")}
            className={`w-full text-left p-3 rounded ${
              rowStyle === "default"
                ? "bg-orange-100 text-orange-700"
                : "hover:bg-gray-100"
            }`}
          >
            <Text>{t("alerts.rowDensity.compact")}</Text>
            <Text className="text-sm text-gray-500">
              {t("alerts.rowDensity.compactDescription")}
            </Text>
          </button>
          <button
            type="button"
            onClick={() => handleStyleChange("relaxed")}
            className={`w-full text-left p-3 rounded ${
              rowStyle === "relaxed"
                ? "bg-orange-100 text-orange-700"
                : "hover:bg-gray-100"
            }`}
          >
            <Text>{t("alerts.rowDensity.relaxed")}</Text>
            <Text className="text-sm text-gray-500">
              {t("alerts.rowDensity.relaxedDescription")}
            </Text>
          </button>
        </div>
      </div>
    </form>
  );
}
