import './globals.css'

export const metadata = {
  title: 'Quản lý Chứng khoán',
  description: 'App quản lý danh mục cá nhân',
}

export default function RootLayout({ children }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  )
}