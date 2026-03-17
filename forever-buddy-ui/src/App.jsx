import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { 
      sender: 'bot', 
      text: 'Здравей! Аз съм твоят **Forever** *Buddy*. 🌿\nПопитай ме за продукти, цени или бизнес възможности!' 
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Скролване най-долу при ново съобщение
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]); // Скролва докато пише

  // Подготовка на историята за Backend-а
  const getHistory = () => {
    const history = [];
    for (let i = 1; i < messages.length - 1; i += 2) {
      if (messages[i].sender === 'user' && messages[i+1]?.sender === 'bot') {
        history.push([messages[i].text, messages[i+1].text]);
      }
    }
    return history;
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userText = input;
    const userMessage = { sender: 'user', text: userText };
    
    // 1. Добавяме веднага съобщението на потребителя
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // --- ВАРИАНТ А: КОМАНДИ (Learn / Forget) ---
      if (userText.toLowerCase().startsWith('/learn ') || userText.toLowerCase().startsWith('/запомни ')) {
        
        const fact = userText.replace(/^\/(learn|запомни)\s+/i, '');
        const response = await fetch('https://foreverbuddy.onrender.com/learn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: fact }),
        });

        if (!response.ok) throw new Error('Failed to learn');
        
        setMessages((prev) => [...prev, { 
          sender: 'bot', 
          text: '✍️ **Разбрано!** Записах тази информация в базата данни.' 
        }]);

      } else if (userText.toLowerCase().startsWith('/forget ') || userText.toLowerCase().startsWith('/забрави ')) {
        
        const fact = userText.replace(/^\/(forget|забрави)\s+/i, '');
        const response = await fetch('https://foreverbuddy.onrender.com/forget', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: fact }),
        });

        if (!response.ok) throw new Error('Failed to forget');
        const data = await response.json();

        setMessages((prev) => [...prev, { 
          sender: 'bot', 
          text: `🗑️ **Операция памет:** ${data.message}` 
        }]);

      } 
      
      // --- ВАРИАНТ Б: СТАНДАРТЕН ЧАТ (СЪС СТРИЙМИНГ) ---
      else {
        const history = getHistory(); 

        // 1. Създаваме ПРАЗНО балонче за бота веднага
        setMessages((prev) => [...prev, { sender: 'bot', text: '' }]);

        const response = await fetch('https://foreverbuddy.onrender.com/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: userText, history: history }),
        });

        if (!response.body) throw new Error('No response body');

        // 2. Започваме да четем потока
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let done = false;
        let accumulatedText = "";

        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          
          if (value) {
            // Декодираме новите букви
            const chunkValue = decoder.decode(value, { stream: true });
            accumulatedText += chunkValue;

            // 3. Обновяваме ПОСЛЕДНОТО съобщение (това на бота) в реално време
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMsgIndex = newMessages.length - 1;
              const lastMsg = newMessages[lastMsgIndex];
              
              // Проверка за сигурност: дали последното наистина е на бота
              if (lastMsg.sender === 'bot') {
                // Създаваме нов обект, за да реагира React на промяната
                newMessages[lastMsgIndex] = { ...lastMsg, text: accumulatedText };
              }
              return newMessages;
            });
          }
        }
      }

    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [...prev, { sender: 'bot', text: 'Грешка при връзката със сървъра.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="chat-header">
        <img src="/Logo.png" alt="Logo" className="logo-img" /> 
      </header>
      
      <div className="chat-window">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.sender}`}>
            <div className={`bubble ${msg.sender}`}>
              <ReactMarkdown>{msg.text}</ReactMarkdown>
            </div>
          </div>
        ))}
        
        
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <div className="input-wrapper">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Попитай нещо..."
            disabled={isLoading}
          />
          <button className="send-btn" onClick={sendMessage} disabled={isLoading || !input.trim()}>
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;