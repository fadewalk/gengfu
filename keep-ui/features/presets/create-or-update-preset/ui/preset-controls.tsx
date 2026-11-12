"use client";
import { Tooltip } from "@/shared/ui";
import { InformationCircleIcon } from "@heroicons/react/24/outline";
import { Switch, Text } from "@tremor/react";
import { useI18n } from "@/i18n/hooks/useI18n";

interface PresetControlsProps {
  isPrivate: boolean;
  setIsPrivate: (value: boolean) => void;
  isNoisy: boolean;
  setIsNoisy: (value: boolean) => void;
  counterShowsFiringOnly: boolean;
  setCounterShowsFiringOnly: (value: boolean) => void;
}

export const PresetControls: React.FC<PresetControlsProps> = ({
  isPrivate,
  setIsPrivate,
  isNoisy,
  setIsNoisy,
  counterShowsFiringOnly,
  setCounterShowsFiringOnly,
}) => {
  const { t } = useI18n();
  return (
    <div className="mt-4">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Switch
            id="private"
            checked={isPrivate}
            onChange={() => setIsPrivate(!isPrivate)}
            color="orange"
          />
          <label htmlFor="private" className="text-sm text-gray-500">
            <Text>{t("misc.presetControls.private")}</Text>
          </label>
          <Tooltip
            content={<>{t("misc.presetControls.privateTooltip")}</>}
            className="z-60"
          >
            <InformationCircleIcon className="w-4 h-4" />
          </Tooltip>
        </div>

        <div className="flex items-center gap-2">
          <Switch
            data-testid="is-noisy-switch"
            id="noisy"
            checked={isNoisy}
            onChange={() => setIsNoisy(!isNoisy)}
            color="orange"
          />
          <label htmlFor="noisy" className="text-sm text-gray-500">
            <Text>{t("misc.presetControls.noisy")}</Text>
          </label>
          <Tooltip
            content={<>{t("misc.presetControls.noisyTooltip")}</>}
            className="z-60"
          >
            <InformationCircleIcon className="w-4 h-4" />
          </Tooltip>
        </div>

        <div className="flex items-center gap-2">
          <Switch
            data-testid="counter-shows-firing-only-switch"
            id="counterShowsFiringOnly"
            checked={counterShowsFiringOnly}
            onChange={() => setCounterShowsFiringOnly(!counterShowsFiringOnly)}
            color="orange"
          />
          <label
            htmlFor="counterShowsFiringOnly"
            className="text-sm text-gray-500"
          >
            <Text>{t("misc.presetControls.counterMode")}</Text>
          </label>
          <Tooltip
            content={<>{t("misc.presetControls.counterModeTooltip")}</>}
            className="z-60"
          >
            <InformationCircleIcon className="w-4 h-4" />
          </Tooltip>
        </div>
      </div>
    </div>
  );
};
