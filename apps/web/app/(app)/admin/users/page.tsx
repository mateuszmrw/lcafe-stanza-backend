"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, UserPlus, Pencil, Trash2, X } from "lucide-react"
import {
  listAdminUsers,
  updateAdminUser,
  createAdminUser,
  deleteAdminUser,
  type UserAdminResponse,
} from "@/src/lib/api/admin"
import { useAuth } from "@/src/stores/auth"
import { cn } from "@/src/lib/cn"

const PROFICIENCY_LEVELS = [
  { value: "A1", label: "A1 — Beginner" },
  { value: "A2", label: "A2 — Elementary" },
  { value: "B1", label: "B1 — Intermediate" },
  { value: "B2", label: "B2 — Upper Intermediate" },
  { value: "C1", label: "C1 — Advanced" },
  { value: "C2", label: "C2 — Proficient" },
]

const NATIVE_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "pl", label: "Polish" },
  { code: "ru", label: "Russian" },
  { code: "de", label: "German" },
  { code: "fr", label: "French" },
  { code: "es", label: "Spanish" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "zh", label: "Chinese" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "ar", label: "Arabic" },
  { code: "uk", label: "Ukrainian" },
  { code: "cs", label: "Czech" },
  { code: "sk", label: "Slovak" },
  { code: "nl", label: "Dutch" },
  { code: "sv", label: "Swedish" },
  { code: "tr", label: "Turkish" },
]

// ── Edit modal ────────────────────────────────────────────────────────────────

interface EditModalProps {
  user: UserAdminResponse
  onClose: () => void
}

function EditModal({ user, onClose }: EditModalProps) {
  const queryClient = useQueryClient()
  const [password, setPassword] = useState("")
  const [proficiency, setProficiency] = useState(user.proficiency_level ?? "")
  const [nativeLang, setNativeLang] = useState(user.native_language_code ?? "")
  const [error, setError] = useState("")

  const mutation = useMutation({
    mutationFn: (data: Parameters<typeof updateAdminUser>[1]) =>
      updateAdminUser(user.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
      onClose()
    },
    onError: (e: Error) => setError(e.message),
  })

  function handleSave() {
    setError("")
    const payload: Parameters<typeof updateAdminUser>[1] = {}
    if (password) payload.password = password
    if (proficiency) payload.proficiency_level = proficiency
    if (nativeLang) payload.native_language_code = nativeLang
    if (!Object.keys(payload).length) { onClose(); return }
    mutation.mutate(payload)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-zinc-100">{user.username}</p>
            <p className="text-xs text-zinc-500">{user.email}</p>
          </div>
          <button onClick={onClose} className="rounded p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">New password</label>
            <input
              type="password"
              placeholder="Leave blank to keep current"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Proficiency level</label>
            <select
              value={proficiency}
              onChange={(e) => setProficiency(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— not set —</option>
              {PROFICIENCY_LEVELS.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Native language</label>
            <select
              value={nativeLang}
              onChange={(e) => setNativeLang(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— not set —</option>
              {NATIVE_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          {error && <p className="rounded-lg bg-red-900/30 px-3 py-2 text-xs text-red-400">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-zinc-400 hover:bg-zinc-800 transition">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={mutation.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
            >
              {mutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Create modal ──────────────────────────────────────────────────────────────

function CreateModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState("user")
  const [proficiency, setProficiency] = useState("")
  const [nativeLang, setNativeLang] = useState("")
  const [error, setError] = useState("")

  const mutation = useMutation({
    mutationFn: createAdminUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
      onClose()
    },
    onError: (e: Error) => setError(e.message),
  })

  function handleCreate() {
    setError("")
    if (!email || !username || !password) {
      setError("Email, username, and password are required")
      return
    }
    mutation.mutate({
      email,
      username,
      password,
      role,
      proficiency_level: proficiency || undefined,
      native_language_code: nativeLang || undefined,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <p className="text-sm font-semibold text-zinc-100">Add user</p>
          <button onClick={onClose} className="rounded p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          <input
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            placeholder="Password (min 8 chars)"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>

          <div className="border-t border-zinc-800 pt-3 space-y-3">
            <p className="text-xs text-zinc-500">Learning profile (optional)</p>
            <select
              value={proficiency}
              onChange={(e) => setProficiency(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Proficiency — not set</option>
              {PROFICIENCY_LEVELS.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
            <select
              value={nativeLang}
              onChange={(e) => setNativeLang(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Native language — not set</option>
              {NATIVE_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          {error && <p className="rounded-lg bg-red-900/30 px-3 py-2 text-xs text-red-400">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-zinc-400 hover:bg-zinc-800 transition">
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={mutation.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
            >
              {mutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Create
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── User row ──────────────────────────────────────────────────────────────────

function UserRow({
  user,
  currentUserId,
  onEdit,
}: {
  user: UserAdminResponse
  currentUserId?: string
  onEdit: (user: UserAdminResponse) => void
}) {
  const queryClient = useQueryClient()
  const isSelf = user.id === currentUserId

  const roleMutation = useMutation({
    mutationFn: (data: { role?: string; is_active?: boolean }) =>
      updateAdminUser(user.id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteAdminUser(user.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  })

  return (
    <tr className="border-b border-zinc-800 hover:bg-zinc-900/50">
      <td className="py-3 px-4">
        <p className="text-sm font-medium text-zinc-200">{user.username}</p>
        <p className="text-xs text-zinc-500">{user.email}</p>
      </td>
      <td className="py-3 px-4 text-xs text-zinc-400">
        {user.proficiency_level
          ? <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-medium text-zinc-200">{user.proficiency_level}</span>
          : <span className="text-zinc-600">—</span>}
        {user.native_language_code && (
          <span className="ml-1.5 text-zinc-500">{user.native_language_code}</span>
        )}
      </td>
      <td className="py-3 px-4">
        {isSelf ? (
          <span className="text-xs text-zinc-500 capitalize">{user.role}</span>
        ) : (
          <select
            value={user.role}
            disabled={roleMutation.isPending}
            onChange={(e) => roleMutation.mutate({ role: e.target.value })}
            className="rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-200 outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        )}
      </td>
      <td className="py-3 px-4">
        {isSelf ? (
          <span className="text-xs text-zinc-500">—</span>
        ) : (
          <button
            onClick={() => roleMutation.mutate({ is_active: !user.is_active })}
            disabled={roleMutation.isPending}
            className={cn(
              "relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50",
              user.is_active ? "bg-blue-600" : "bg-zinc-700"
            )}
            aria-label={user.is_active ? "Deactivate" : "Activate"}
          >
            <span className={cn(
              "inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform",
              user.is_active ? "translate-x-4.5" : "translate-x-0.5"
            )} />
          </button>
        )}
      </td>
      <td className="py-3 px-4 text-xs text-zinc-500">
        {new Date(user.created_at).toLocaleDateString()}
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-1">
          <button
            onClick={() => onEdit(user)}
            className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200 transition"
            aria-label="Edit user"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          {!isSelf && (
            <button
              onClick={() => {
                if (confirm(`Delete user "${user.username}"? This cannot be undone.`)) {
                  deleteMutation.mutate()
                }
              }}
              disabled={deleteMutation.isPending}
              className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-red-400 transition disabled:opacity-50"
              aria-label="Delete user"
            >
              {deleteMutation.isPending
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <Trash2 className="h-3.5 w-3.5" />}
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth()
  const [editingUser, setEditingUser] = useState<UserAdminResponse | null>(null)
  const [creating, setCreating] = useState(false)

  const { data: users, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => listAdminUsers(),
  })

  if (isLoading) return <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-zinc-400">
          Manage user accounts. You cannot modify or delete your own account.
        </p>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 transition"
        >
          <UserPlus className="h-4 w-4" />
          Add user
        </button>
      </div>

      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">User</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Level</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Role</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Active</th>
              <th className="py-3 px-4 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">Joined</th>
              <th className="py-3 px-4" />
            </tr>
          </thead>
          <tbody className="bg-zinc-950">
            {users?.map((u) => (
              <UserRow
                key={u.id}
                user={u}
                currentUserId={currentUser?.id}
                onEdit={setEditingUser}
              />
            ))}
          </tbody>
        </table>
        {users?.length === 0 && (
          <p className="py-8 text-center text-sm text-zinc-600">No users found.</p>
        )}
      </div>

      {editingUser && <EditModal user={editingUser} onClose={() => setEditingUser(null)} />}
      {creating && <CreateModal onClose={() => setCreating(false)} />}
    </div>
  )
}
