"use client"

import { use, useEffect, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { ArrowLeft, CheckCircle2, XCircle } from "lucide-react"
import {
  getExercises,
  completeExercises,
  type Exercise,
  type ClozeExercise,
  type MeaningRecallExercise,
  type GrammarMicroDrillExercise,
  type ExerciseAnswer,
  type ExerciseCompleteResponse,
} from "@/src/lib/api/exercises"

type Phase = "loading" | "exercise" | "results" | "error"

interface AnswerState {
  value: string
  submitted: boolean
  correct: boolean | null
  correctForm: string
}

export default function ExercisesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = (searchParams.get("mode") ?? "inline") as "inline" | "practice"
  const returnPage = Number(searchParams.get("returnPage") ?? "1")
  const endOfContent = searchParams.get("endOfContent") === "true"

  const [phase, setPhase] = useState<Phase>("loading")
  const [sessionId, setSessionId] = useState("")
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [current, setCurrent] = useState(0)
  const [answerStates, setAnswerStates] = useState<Record<string, AnswerState>>({})
  const [clozeInput, setClozeInput] = useState("")
  const [results, setResults] = useState<ExerciseCompleteResponse | null>(null)
  const [completing, setCompleting] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getExercises(id, mode, returnPage)
      .then((data) => {
        if (data.exercises.length === 0) {
          navigateBack()
          return
        }
        setSessionId(data.session_id)
        setExercises(data.exercises)
        setPhase("exercise")
      })
      .catch(() => setPhase("error"))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (phase === "exercise") {
      setClozeInput("")
      inputRef.current?.focus()
    }
  }, [phase, current])

  function navigateBack() {
    if (endOfContent) {
      router.push("/library")
    } else {
      router.push(`/reader/${id}?page=${returnPage}`)
    }
  }

  function currentExercise(): Exercise | undefined {
    return exercises[current]
  }

  function submitAnswer(answer: string) {
    const ex = currentExercise()
    if (!ex) return
    const state = answerStates[ex.id]
    if (state?.submitted) return

    let correct = false
    let correctForm = ""

    if (ex.type === "cloze") {
      correctForm = ex.correct_form
      correct = answer.trim().toLowerCase() === ex.correct_form.toLowerCase()
    } else if (ex.type === "meaning_recall") {
      correctForm = ex.options[ex.correct_index]
      correct = answer === String(ex.correct_index)
    } else if (ex.type === "grammar_micro_drill") {
      correctForm = ex.options[ex.correct_index]
      correct = answer === String(ex.correct_index)
    }

    setAnswerStates((prev) => ({
      ...prev,
      [ex.id]: { value: answer, submitted: true, correct, correctForm },
    }))
  }

  async function handleNext() {
    if (current < exercises.length - 1) {
      setCurrent((c) => c + 1)
      setClozeInput("")
    } else {
      await submitAll()
    }
  }

  async function submitAll() {
    setCompleting(true)
    const answers: ExerciseAnswer[] = exercises.map((ex) => {
      const state = answerStates[ex.id]
      return {
        exercise_id: ex.id,
        word_id: ex.word_id,
        answer: state?.value ?? "",
        exercise_type: ex.type,
      }
    })

    try {
      const res = await completeExercises(id, { session_id: sessionId, page: returnPage, answers })
      setResults(res)
      setPhase("results")
    } catch (err: unknown) {
      const status = err && typeof err === "object" && "status" in err ? (err as { status: number }).status : 0
      if (status === 404) {
        alert("Session expired — your progress wasn't saved.")
      }
      navigateBack()
    } finally {
      setCompleting(false)
    }
  }

  const ex = currentExercise()
  const currentState = ex ? answerStates[ex.id] : undefined

  if (phase === "loading") {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-blue-500" />
      </div>
    )
  }

  if (phase === "error") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-zinc-400">Failed to load exercises.</p>
        <button onClick={navigateBack} className="text-sm text-blue-400 hover:text-blue-300">
          Go back
        </button>
      </div>
    )
  }

  if (phase === "results" && results) {
    const correctCount = results.results.filter((r) => r.correct).length
    const total = results.results.length

    return (
      <div className="flex h-full flex-col items-center justify-center px-4">
        <div className="w-full max-w-lg rounded-xl border border-zinc-700 bg-zinc-900 p-8">
          <div className="mb-6 text-center">
            <div className="mb-2 text-4xl font-bold text-zinc-100">
              {correctCount}/{total}
            </div>
            <p className="text-sm text-zinc-400">
              {correctCount === total ? "Perfect! All correct." : `${total - correctCount} to keep working on.`}
            </p>
          </div>

          {results.upgrades.length > 0 && (
            <div className="mb-6">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
                Words upgraded
              </p>
              <div className="space-y-1">
                {results.upgrades.map((u) => (
                  <div key={u.word_id} className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                    <span className="font-medium text-zinc-200">{u.lemma}</span>
                    <span className="text-zinc-500">
                      {u.old_status} → {u.new_status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={navigateBack}
            className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500"
          >
            {endOfContent ? "Back to Library" : "Continue reading"}
          </button>
        </div>
      </div>
    )
  }

  if (!ex) return null

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center gap-4 border-b border-zinc-800 bg-zinc-900 px-6 py-3">
        <button
          onClick={navigateBack}
          className="rounded-md p-1 text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100"
          aria-label="Back"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <span className="flex-1 text-sm font-medium text-zinc-300">Practice</span>
        <span className="text-xs text-zinc-500">
          {current + 1} / {exercises.length}
        </span>
      </header>

      {/* Progress bar */}
      <div className="h-0.5 w-full bg-zinc-800">
        <div
          className="h-full bg-blue-500 transition-all duration-300"
          style={{ width: `${Math.round(((current + (currentState?.submitted ? 1 : 0)) / exercises.length) * 100)}%` }}
        />
      </div>

      {/* Exercise card */}
      <div className="flex flex-1 items-center justify-center overflow-y-auto px-4 py-8">
        <div className="w-full max-w-lg">
          {ex.type === "cloze" && (
            <ClozeCard
              ex={ex}
              state={currentState}
              input={clozeInput}
              inputRef={inputRef}
              onInput={setClozeInput}
              onSubmit={() => submitAnswer(clozeInput)}
              onNext={handleNext}
              isLast={current === exercises.length - 1}
              completing={completing}
            />
          )}
          {ex.type === "meaning_recall" && (
            <MeaningRecallCard
              ex={ex}
              state={currentState}
              onSubmit={(idx) => submitAnswer(String(idx))}
              onNext={handleNext}
              isLast={current === exercises.length - 1}
              completing={completing}
            />
          )}
          {ex.type === "grammar_micro_drill" && (
            <GrammarCard
              ex={ex}
              state={currentState}
              onSubmit={(idx) => submitAnswer(String(idx))}
              onNext={handleNext}
              isLast={current === exercises.length - 1}
              completing={completing}
            />
          )}
        </div>
      </div>
    </div>
  )
}

function ClozeCard({
  ex,
  state,
  input,
  inputRef,
  onInput,
  onSubmit,
  onNext,
  isLast,
  completing,
}: {
  ex: ClozeExercise
  state: AnswerState | undefined
  input: string
  inputRef: React.RefObject<HTMLInputElement | null>
  onInput: (v: string) => void
  onSubmit: () => void
  onNext: () => void
  isLast: boolean
  completing: boolean
}) {
  const tokens = ex.sentence_tokens.map((t, i) =>
    i === ex.blank_index ? (
      <span key={i} className="mx-0.5 inline-block min-w-[3rem] border-b-2 border-blue-500 text-center font-medium text-blue-300">
        {state?.submitted ? (
          <span className={state.correct ? "text-emerald-400" : "text-red-400"}>{state.value || "—"}</span>
        ) : (
          "___"
        )}
      </span>
    ) : (
      <span key={i}>{t} </span>
    )
  )

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-6">
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-zinc-500">Fill in the blank</p>
      <p className="mb-1 text-xs text-zinc-600">Lemma: <span className="text-zinc-400">{ex.lemma}</span></p>
      <p className="mb-5 text-base leading-relaxed text-zinc-200">{tokens}</p>

      {!state?.submitted ? (
        <div className="flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => onInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && input.trim()) onSubmit() }}
            placeholder="Type the word…"
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:outline-none"
          />
          <button
            onClick={onSubmit}
            disabled={!input.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-40"
          >
            Submit
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <Feedback correct={state.correct!} correctForm={state.correctForm} userAnswer={state.value} />
          <NextButton onClick={onNext} isLast={isLast} completing={completing} />
        </div>
      )}
    </div>
  )
}

function MeaningRecallCard({
  ex,
  state,
  onSubmit,
  onNext,
  isLast,
  completing,
}: {
  ex: MeaningRecallExercise
  state: AnswerState | undefined
  onSubmit: (idx: number) => void
  onNext: () => void
  isLast: boolean
  completing: boolean
}) {
  const parts = ex.sentence.split(ex.highlighted_word)

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-6">
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-zinc-500">What does it mean?</p>
      <p className="mb-5 text-base leading-relaxed text-zinc-200">
        {parts[0]}
        <span className="rounded bg-blue-900/40 px-0.5 font-medium text-blue-300">{ex.highlighted_word}</span>
        {parts.slice(1).join(ex.highlighted_word)}
      </p>

      <div className="mb-4 grid grid-cols-2 gap-2">
        {ex.options.map((opt, i) => {
          const chosen = state?.submitted && state.value === String(i)
          const isCorrect = i === ex.correct_index
          let cls = "min-h-[48px] rounded-lg border px-3 py-2 text-sm text-left transition"
          if (!state?.submitted) {
            cls += " border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800"
          } else if (isCorrect) {
            cls += " border-emerald-600 bg-emerald-900/30 text-emerald-300"
          } else if (chosen) {
            cls += " border-red-600 bg-red-900/30 text-red-300"
          } else {
            cls += " border-zinc-800 text-zinc-600"
          }
          return (
            <button key={i} onClick={() => !state?.submitted && onSubmit(i)} className={cls}>
              {opt}
            </button>
          )
        })}
      </div>

      {state?.submitted && (
        <div className="space-y-3">
          <Feedback correct={state.correct!} correctForm={state.correctForm} />
          <NextButton onClick={onNext} isLast={isLast} completing={completing} />
        </div>
      )}
    </div>
  )
}

function GrammarCard({
  ex,
  state,
  onSubmit,
  onNext,
  isLast,
  completing,
}: {
  ex: GrammarMicroDrillExercise
  state: AnswerState | undefined
  onSubmit: (idx: number) => void
  onNext: () => void
  isLast: boolean
  completing: boolean
}) {
  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-6">
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-zinc-500">Grammar</p>
      <p className="mb-5 text-base leading-relaxed text-zinc-200">{ex.prompt}</p>

      <div className="mb-4 grid grid-cols-2 gap-2">
        {ex.options.map((opt, i) => {
          const chosen = state?.submitted && state.value === String(i)
          const isCorrect = i === ex.correct_index
          let cls = "min-h-[48px] rounded-lg border px-3 py-2 text-sm text-left transition"
          if (!state?.submitted) {
            cls += " border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800"
          } else if (isCorrect) {
            cls += " border-emerald-600 bg-emerald-900/30 text-emerald-300"
          } else if (chosen) {
            cls += " border-red-600 bg-red-900/30 text-red-300"
          } else {
            cls += " border-zinc-800 text-zinc-600"
          }
          return (
            <button key={i} onClick={() => !state?.submitted && onSubmit(i)} className={cls}>
              {opt}
            </button>
          )
        })}
      </div>

      {state?.submitted && (
        <div className="space-y-3">
          <Feedback correct={state.correct!} correctForm={state.correctForm} />
          <NextButton onClick={onNext} isLast={isLast} completing={completing} />
        </div>
      )}
    </div>
  )
}

function Feedback({ correct, correctForm, userAnswer }: { correct: boolean; correctForm: string; userAnswer?: string }) {
  return (
    <div className={`flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${correct ? "bg-emerald-900/30 text-emerald-300" : "bg-red-900/30 text-red-300"}`}>
      {correct ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0" />}
      <span>
        {correct
          ? "Correct!"
          : <>Correct answer: <strong>{correctForm}</strong>{userAnswer ? ` (you said: ${userAnswer})` : ""}</>}
      </span>
    </div>
  )
}

function NextButton({ onClick, isLast, completing }: { onClick: () => void; isLast: boolean; completing: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={completing}
      className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
    >
      {completing ? "Saving…" : isLast ? "See results" : "Next"}
    </button>
  )
}
