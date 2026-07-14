import { create } from 'zustand';

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger';
  onConfirm: () => void;
}

interface ConfirmState extends ConfirmOptions {
  open: boolean;
  confirm: (opts: ConfirmOptions) => void;
  resolve: () => void;
  cancel: () => void;
}

export const useConfirmStore = create<ConfirmState>((set, get) => ({
  open: false,
  message: '',
  onConfirm: () => {},
  confirm: (opts) => set({ ...opts, open: true }),
  resolve: () => {
    const { onConfirm } = get();
    onConfirm();
    set({ open: false });
  },
  cancel: () => set({ open: false }),
}));
