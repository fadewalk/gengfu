"use client";

import { useState } from "react";
import { Button, TextInput, Subtitle, Callout } from "@tremor/react";
import Modal from "@/components/ui/Modal";
import { useApi } from "@/shared/lib/hooks/useApi";
import { KeepApiError } from "@/shared/api";
import { showSuccessToast } from "@/shared/ui";
import { useI18n } from "@/i18n/hooks/useI18n";

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ChangePasswordModal = ({
  isOpen,
  onClose,
}: ChangePasswordModalProps) => {
  const { t } = useI18n();
  const api = useApi();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const resetForm = () => {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setError(null);
    setIsSubmitting(false);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!currentPassword) {
      setError(t("settings.changePassword.errors.currentRequired"));
      return;
    }
    if (!newPassword) {
      setError(t("settings.changePassword.errors.newRequired"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t("settings.changePassword.errors.mismatch"));
      return;
    }
    if (newPassword === currentPassword) {
      setError(t("settings.changePassword.errors.sameAsCurrent"));
      return;
    }

    setIsSubmitting(true);
    try {
      await api.put("/auth/users/me/password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      showSuccessToast(t("settings.changePassword.success"));
      handleClose();
    } catch (err) {
      if (err instanceof KeepApiError) {
        setError(err.message || t("settings.changePassword.errors.failed"));
      } else {
        setError(t("settings.changePassword.errors.unexpected"));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={t("settings.changePassword.title")}
      className="w-[400px]"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <Subtitle>{t("settings.changePassword.currentPassword")}</Subtitle>
          <TextInput
            type="password"
            placeholder={t("settings.changePassword.currentPlaceholder")}
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <div>
          <Subtitle>{t("settings.changePassword.newPassword")}</Subtitle>
          <TextInput
            type="password"
            placeholder={t("settings.changePassword.newPlaceholder")}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>
        <div>
          <Subtitle>{t("settings.changePassword.confirmNewPassword")}</Subtitle>
          <TextInput
            type="password"
            placeholder={t("settings.changePassword.confirmPlaceholder")}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>
        {error && (
          <Callout title={t("common.error")} color="rose">
            {error}
          </Callout>
        )}
        <div className="flex justify-end gap-2 mt-2">
          <Button
            type="button"
            variant="secondary"
            color="orange"
            className="border border-orange-500 text-orange-500"
            onClick={handleClose}
          >
            {t("common.cancel")}
          </Button>
          <Button
            type="submit"
            color="orange"
            disabled={isSubmitting}
            loading={isSubmitting}
          >
            {isSubmitting ? t("settings.changePassword.saving") : t("settings.changePassword.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
