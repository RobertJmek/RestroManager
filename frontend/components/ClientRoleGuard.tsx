"use client";

import RoleGuard from "./RoleGuard";

type RoleGuardProps = {
  role: "Manager" | "Waiter" | "Chef";
  theme?: "dark" | "light";
  spinnerColor?: string;
  children: React.ReactNode;
};

export default function ClientRoleGuard(props: RoleGuardProps) {
  return <RoleGuard {...props} />;
}
