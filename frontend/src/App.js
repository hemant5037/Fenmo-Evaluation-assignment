import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || '';

function App() {
    const [expenses, setExpenses] = useState([]);
    const [amount, setAmount] = useState('');
    const [category, setCategory] = useState('');
    const [description, setDescription] = useState('');
    const [date, setDate] = useState(() => {
        const d = new Date();
        return d.toISOString().slice(0, 10);
    });
    const [filterCategory, setFilterCategory] = useState('');
    const [sortByDateDesc, setSortByDateDesc] = useState(true);
    const [loading, setLoading] = useState(false);
    const [submitLoading, setSubmitLoading] = useState(false);
    const [error, setError] = useState(null);
    const [submitError, setSubmitError] = useState(null);

    const fetchExpenses = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            if (filterCategory) params.set('category', filterCategory);
            params.set('sort', sortByDateDesc ? 'date_desc' : 'date_asc');
            const url = `${API_BASE}/expenses${params.toString() ? '?' + params : ''}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load expenses');
            const data = await response.json();
            setExpenses(data);
        } catch (err) {
            const msg = err.message === 'Failed to fetch'
                ? 'Cannot reach the server. Is the backend running? (python backend.py on port 5001)'
                : (err.message || 'Failed to load expenses');
            setError(msg);
            setExpenses([]);
        } finally {
            setLoading(false);
        }
    }, [filterCategory, sortByDateDesc]);

    useEffect(() => {
        fetchExpenses();
    }, [fetchExpenses]);

    const addExpense = async (e) => {
        e.preventDefault();
        setSubmitError(null);
        setSubmitLoading(true);
        try {
            const payload = { amount: parseFloat(amount), category, description, date };
            const response = await fetch(`${API_BASE}/expenses`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to add expense');
            }
            setAmount('');
            setCategory('');
            setDescription('');
            setDate(new Date().toISOString().slice(0, 10));
            await fetchExpenses();
        } catch (err) {
            setSubmitError(err.message || 'Failed to add expense');
        } finally {
            setSubmitLoading(false);
        }
    };

    const categories = ['Food', 'Transport', 'Utilities', 'Entertainment', 'Shopping', 'Healthcare', 'Other'];
    const uniqueCategories = [...new Set([...categories, ...expenses.map((e) => e.category)])].sort();

    const totalAmount = expenses.reduce((acc, e) => acc + (e.amount || 0), 0);

    const formatCurrency = (val) => `₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    return (
        <div className="App">
            <header className="app-header">
                <h1>Expense Tracker</h1>
                <p>Track where your money goes</p>
            </header>

            <section className="add-expense-card">
                <h3>Add new expense</h3>
                <form onSubmit={addExpense}>
                    <div className="form-grid">
                        <div className="form-group">
                            <label>Amount (₹)</label>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                placeholder="0.00"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                required
                                disabled={submitLoading}
                            />
                        </div>
                        <div className="form-group">
                            <label>Category</label>
                            <input
                                list="categories"
                                type="text"
                                placeholder="e.g. Food, Transport"
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                required
                                disabled={submitLoading}
                            />
                            <datalist id="categories">
                                {uniqueCategories.map((c) => (
                                    <option key={c} value={c} />
                                ))}
                            </datalist>
                        </div>
                        <div className="form-group full-width">
                            <label>Description</label>
                            <input
                                type="text"
                                placeholder="What was this expense for?"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                required
                                disabled={submitLoading}
                            />
                        </div>
                        <div className="form-group">
                            <label>Date</label>
                            <input
                                type="date"
                                value={date}
                                onChange={(e) => setDate(e.target.value)}
                                required
                                disabled={submitLoading}
                            />
                        </div>
                        <div className="full-width">
                            <button type="submit" disabled={submitLoading}>
                                {submitLoading ? 'Adding…' : '+ Add Expense'}
                            </button>
                        </div>
                    </div>
                    {submitError && <p className="submit-error">{submitError}</p>}
                </form>
            </section>

            <div className="controls-card">
                <label>
                    Filter:
                    <select
                        value={filterCategory}
                        onChange={(e) => setFilterCategory(e.target.value)}
                    >
                        <option value="">All Categories</option>
                        {uniqueCategories.map((c) => (
                            <option key={c} value={c}>{c}</option>
                        ))}
                    </select>
                </label>
                <label>
                    <input
                        type="checkbox"
                        checked={sortByDateDesc}
                        onChange={(e) => setSortByDateDesc(e.target.checked)}
                    />
                    Newest first
                </label>
            </div>

            <section className="total-card">
                <div className="label">Total expenses</div>
                <div className="amount">{formatCurrency(totalAmount)}</div>
            </section>

            <section className="expense-list-card">
                {loading ? (
                    <div className="loading-state">
                        <span className="loading-spinner" />
                        Loading expenses…
                    </div>
                ) : error ? (
                    <div className="error-state">{error}</div>
                ) : expenses.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📋</div>
                        <p>No expenses yet.<br />Add one above to get started.</p>
                    </div>
                ) : (
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Category</th>
                                <th>Description</th>
                                <th>Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {expenses.map((exp) => (
                                <tr key={exp.id}>
                                    <td>{exp.date}</td>
                                    <td><span className="category-badge">{exp.category}</span></td>
                                    <td>{exp.description}</td>
                                    <td className="amount-cell">{formatCurrency(exp.amount)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>
        </div>
    );
}

export default App;
