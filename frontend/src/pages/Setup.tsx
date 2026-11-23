import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBootstrap, useCompleteBootstrap } from '../api/queries'
import { ErrorState } from '../components/ErrorState'
import { Field } from '../components/Field'
import { TIMEZONE_OPTIONS } from '../lib/date'

export function Setup() {
  const bootstrap = useBootstrap()
  const complete = useCompleteBootstrap()
  const navigate = useNavigate()

  const [timezone, setTimezone] = useState('')
  const [termStart, setTermStart] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (bootstrap.data && timezone === '') {
      setTimezone(bootstrap.data.timezone)
    }
  }, [bootstrap.data, timezone])

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!timezone.trim()) {
      setError('请填写 IANA 时区，例如 Asia/Shanghai。')
      return
    }
    if (!termStart) {
      setError('请选择第一教学周的周一日期。')
      return
    }
    setError(null)
    complete.mutate(
      { timezone: timezone.trim(), term_start_date: termStart },
      {
        onSuccess: () => {
          navigate('/today', { replace: true })
        },
      },
    )
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 md:py-12">
      <header className="mb-6 space-y-2">
        <p className="text-xs uppercase tracking-[0.2em] text-muted">Student Workbench</p>
        <h1 className="text-2xl font-semibold text-ink">首次引导</h1>
        <p className="text-sm text-muted">
          数据只保存在这台电脑。教务与学习平台的账号密码仅用于当次登录，除非你明确选择保存到系统凭据库。
        </p>
      </header>

      {bootstrap.isError ? (
        <div className="mb-4">
          <ErrorState
            error={bootstrap.error}
            title="无法读取引导状态"
            onRetry={() => void bootstrap.refetch()}
          />
        </div>
      ) : null}

      <section className="card card-pad mb-4 space-y-3">
        <h2 className="text-sm font-semibold text-ink">本地数据说明</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
          <li>数据写入本机 SQLite，不上传云端；密码与验证码不会进入浏览器持久化存储。</li>
          <li>课程表与作业同步均为只读，不会修改学校平台上的内容。</li>
          <li>Git 扫描只读取本地仓库状态，不会提交或推送代码。</li>
        </ul>
      </section>

      <form className="card card-pad space-y-4" onSubmit={handleSubmit}>
        <h2 className="text-sm font-semibold text-ink">基础设置</h2>

        <Field
          label="时区"
          htmlFor="setup-timezone"
          required
          hint="用于解释“今天”和逾期边界，例如 Asia/Shanghai。"
        >
          <input
            id="setup-timezone"
            className="input"
            list="setup-timezone-options"
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
            autoComplete="off"
          />
          <datalist id="setup-timezone-options">
            {TIMEZONE_OPTIONS.map((zone) => (
              <option key={zone} value={zone} />
            ))}
          </datalist>
        </Field>

        <Field
          label="第一教学周的周一"
          htmlFor="setup-term-start"
          required
          hint="教务课程表按该日期推算教学周与单双周，后续可在设置中修改。"
        >
          <input
            id="setup-term-start"
            className="input"
            type="date"
            value={termStart}
            onChange={(event) => setTermStart(event.target.value)}
          />
        </Field>

        {error ? (
          <p role="alert" className="text-sm text-rose-300">
            {error}
          </p>
        ) : null}

        {complete.isError ? (
          <ErrorState error={complete.error} title="完成引导失败" />
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={complete.isPending}
          >
            {complete.isPending ? '正在保存…' : '完成引导'}
          </button>
          <p className="text-xs text-muted">
            稍后可以在同步中心添加教务与学习平台连接。
          </p>
        </div>
      </form>
    </div>
  )
}
